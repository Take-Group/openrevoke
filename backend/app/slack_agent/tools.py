"""The three tools the language model gets. Each call runs in its own database transaction.

The requester is fixed by the Slack user who wrote, never by the model's
arguments, so a prompt cannot make the agent act for someone else.
"""

import json
from typing import TYPE_CHECKING, Any

from sqlalchemy import func, or_, select

from app.ai.base import ToolError, ToolSpec
from app.database import async_session
from app.models import AccessRequest, Account, Action, App, Person
from app.models.enums import (
    OPEN_REQUEST_STATUSES,
    AccessRequestStatus,
    AccountStatus,
    ActionKind,
    RequestPolicy,
)
from app.schemas.actions import WriteKind
from app.services.access.outcomes import Outcome, SlackOrigin
from app.services.access.requests import NewRequest, request_access
from app.services.actions import OPEN_STATUSES
from app.services.errors import DomainError

if TYPE_CHECKING:
    import uuid

    from sqlalchemy.ext.asyncio import AsyncSession

    from app.services.action_dispatch import ActionDispatcher

MAX_APPS = 300

TOOLS = [
    ToolSpec(
        name="list_apps",
        description=(
            "All company apps tracked in Open Revoke, with whether the person can ask for an account, "
            "whether they already have one and whether a request is open. Use it to find the app the person means."
        ),
        parameters={"type": "object", "properties": {}, "additionalProperties": False},
    ),
    ToolSpec(
        name="my_access",
        description="The person's current accounts in company apps and their open access requests.",
        parameters={"type": "object", "properties": {}, "additionalProperties": False},
    ),
    ToolSpec(
        name="request_access",
        description=(
            "Ask for an account for the person in one app. Returns what happens next. "
            "Call it once per app, with the app's `app` id from list_apps and the person's own reason. "
            'If the person did not say why they need the app, ask them "Why do you need it?" first.'
        ),
        parameters={
            "type": "object",
            "properties": {
                "app": {"type": "string", "description": "The `app` id from list_apps"},
                "justification": {
                    "type": "string",
                    "description": "Why the person needs the app, in their words; their manager or an admin reads it",
                },
                "role": {"type": "string", "description": "Role the person asked for, if any (e.g. admin, member)"},
            },
            "required": ["app", "justification"],
            "additionalProperties": False,
        },
    ),
]

POLICY_TEXT = {
    RequestPolicy.AUTOMATIC: "granted automatically (still give a reason)",
    RequestPolicy.MANAGER: "the person's manager approves; ask why they need it",
    RequestPolicy.MANAGER_THEN_ADMIN: "the manager, then an admin approves; ask why they need it",
    RequestPolicy.ADMIN: "an admin approves; ask why they need it",
    RequestPolicy.OFF: "not available on request, an admin decides",
}

REQUEST_STATUS_TEXT = {
    AccessRequestStatus.PENDING_MANAGER: "waits for the manager",
    AccessRequestStatus.PENDING_ADMIN: "waits for an admin",
    AccessRequestStatus.APPROVED: "approved, the account is being created",
}

OUTCOME_TEXT = {
    Outcome.IN_PROGRESS: "Approved. Open Revoke is creating the account now.",
    Outcome.WAITING_FOR_MANAGER: "The request waits for the person's manager (named in `note`) to approve it.",
    Outcome.WAITING_FOR_APPROVAL: "The request waits for an admin's approval (`note` may say why).",
    Outcome.WAITING_FOR_ADMIN: (
        "Approved. The app has no automatic connection, so an admin creates the account by hand."
    ),
    Outcome.ALREADY_HAS_ACCOUNT: "The person already has an account in this app. Nothing was requested.",
    Outcome.ALREADY_REQUESTED: "A request for this app is already open. Nothing new was requested.",
    Outcome.NOT_AVAILABLE: "This app is not available on request. The person should ask an admin directly.",
}


class AgentTools:
    def __init__(self, *, person_id: uuid.UUID, origin: SlackOrigin, dispatcher: ActionDispatcher) -> None:
        self._person_id = person_id
        self._origin = origin
        self._dispatcher = dispatcher

    async def execute(self, name: str, arguments: dict[str, Any]) -> str:
        async with async_session() as session:
            try:
                if name == "list_apps":
                    result = await self._list_apps(session)
                elif name == "my_access":
                    result = await self._my_access(session)
                elif name == "request_access":
                    result = await self._request_access(session, arguments)
                else:
                    raise ToolError(f"Unknown tool {name}")
                await session.commit()
            except DomainError as exc:
                await session.rollback()
                raise ToolError(exc.message) from exc
        return json.dumps(result, ensure_ascii=False)

    async def _list_apps(self, session: AsyncSession) -> dict[str, Any]:
        apps = list(await session.scalars(select(App).order_by(func.lower(App.name)).limit(MAX_APPS)))
        has_account = await _apps_with_account(session, self._person_id)
        open_requests = await _apps_with_open_request(session, self._person_id)
        return {
            "apps": [
                {
                    "app": app.slug,
                    "name": app.name,
                    "on_request": POLICY_TEXT[app.request_policy],
                    "you_have_account": app.id in has_account,
                    "request_open": app.id in open_requests,
                }
                for app in apps
            ]
        }

    async def _my_access(self, session: AsyncSession) -> dict[str, Any]:
        rows = await session.execute(
            select(App.name, Account.email, Account.role, Account.status)
            .join(App, App.id == Account.app_id)
            .where(Account.person_id == self._person_id, Account.status != AccountStatus.REMOVED)
            .order_by(func.lower(App.name))
        )
        requests = await session.execute(
            select(App.name, AccessRequest.status)
            .join(App, App.id == AccessRequest.app_id)
            .where(AccessRequest.person_id == self._person_id, AccessRequest.status.in_(OPEN_REQUEST_STATUSES))
            .order_by(func.lower(App.name))
        )
        return {
            "accounts": [
                {"app": name, "email": email, "role": role, "status": str(status)} for name, email, role, status in rows
            ],
            "open_requests": [{"app": name, "status": REQUEST_STATUS_TEXT[status]} for name, status in requests],
        }

    async def _request_access(self, session: AsyncSession, arguments: dict[str, Any]) -> dict[str, Any]:
        key = str(arguments.get("app") or "").strip()
        if not key:
            raise ToolError("Give the `app` id from list_apps")
        app = await session.scalar(
            select(App).where(or_(App.slug == key.lower(), func.lower(App.name) == key.lower())).limit(1)
        )
        if app is None:
            raise ToolError(f"No app {key!r}. Call list_apps and use an `app` id from it")
        person = await session.get(Person, self._person_id)
        if person is None:
            raise ToolError("The person is no longer in Open Revoke")
        justification = str(arguments.get("justification") or "").strip()
        if not justification:
            raise ToolError('Ask the person "Why do you need it?", then call request_access with their answer')
        new = NewRequest(
            justification=justification,
            requested_by=f"{person.primary_email} (Slack)",
            role=str(arguments.get("role") or "").strip() or None,
            origin=self._origin,
        )
        result = await request_access(session, person=person, app=app, new=new, dispatcher=self._dispatcher)
        answer = {"app": result.app_name, "result": str(result.outcome), "meaning": OUTCOME_TEXT[result.outcome]}
        if result.note:
            answer["note"] = result.note
        return answer


def _creation() -> Any:
    return or_(
        Action.kind == ActionKind.CREATE_ACCOUNT,
        Action.payload["operation"].astext == WriteKind.CREATE_ACCOUNT,
    )


async def _apps_with_account(session: AsyncSession, person_id: uuid.UUID) -> set[uuid.UUID]:
    rows = await session.scalars(
        select(Account.app_id).where(Account.person_id == person_id, Account.status != AccountStatus.REMOVED)
    )
    return set(rows)


async def _apps_with_open_request(session: AsyncSession, person_id: uuid.UUID) -> set[uuid.UUID]:
    """Apps with an unfinished request, or an open account creation an admin started."""
    actions = await session.scalars(
        select(Action.app_id).where(Action.person_id == person_id, Action.status.in_(OPEN_STATUSES), _creation())
    )
    requests = await session.scalars(
        select(AccessRequest.app_id).where(
            AccessRequest.person_id == person_id, AccessRequest.status.in_(OPEN_REQUEST_STATUSES)
        )
    )
    return set(actions) | set(requests)
