"""Access requests: a person asks for an account in an app, in Slack (the agent) or on the panel.

The request becomes a ``create_account`` action (or a manual task) with reason
``self_service``. The app's ``self_service`` policy decides what happens next:
``off`` refuses, ``approval`` leaves the action for an admin, ``automatic``
approves it at once. A connector write still needs "Allow writes" on the
connection; without it the action waits for an admin like with ``approval``.
"""

import enum
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import func, select

from app.models import AccessRequest, Action, App, Person
from app.models.enums import (
    AccessRequestChannel,
    AccessRequestStatus,
    ActionKind,
    ActionReason,
    ActionStatus,
    PersonStatus,
    SelfServicePolicy,
)
from app.schemas.actions import ActionCreate, WriteKind
from app.schemas.slack_agent import AccessRequestOut, AccessRequestPage
from app.services import audit
from app.services.action_approval import approve
from app.services.actions import create_action
from app.services.errors import InvalidInputError
from app.services.onboarding import apps_with_account, apps_with_open_creation
from app.services.presenters import app_ref, person_ref

if TYPE_CHECKING:
    import uuid

    from sqlalchemy.ext.asyncio import AsyncSession

    from app.services.action_dispatch import ActionDispatcher


class Outcome(enum.StrEnum):
    IN_PROGRESS = "in_progress"  # approved, the connector is creating the account now
    WAITING_FOR_APPROVAL = "waiting_for_approval"
    WAITING_FOR_ADMIN = "waiting_for_admin"  # approved manual task: an admin creates the account by hand
    ALREADY_HAS_ACCOUNT = "already_has_account"
    ALREADY_REQUESTED = "already_requested"
    NOT_AVAILABLE = "not_available"  # the app's policy is off


@dataclass(frozen=True)
class RequestResult:
    outcome: Outcome
    app_name: str
    action_id: uuid.UUID | None = None
    note: str | None = None


@dataclass(frozen=True)
class SlackOrigin:
    user_id: str
    channel_id: str
    message: str | None


async def request_access(
    session: AsyncSession,
    *,
    person: Person,
    app: App,
    role: str | None,
    dispatcher: ActionDispatcher,
    origin: SlackOrigin | None = None,
    message: str | None = None,
) -> RequestResult:
    """``origin`` set: asked in Slack (the agent answers there). None: asked on the panel, ``message`` is the note."""
    if person.status == PersonStatus.LEFT:
        raise InvalidInputError("The person has left the company")
    name = app.name  # approve() below expires the session's objects
    if app.self_service == SelfServicePolicy.OFF:
        return RequestResult(Outcome.NOT_AVAILABLE, name)
    if app.id in await apps_with_account(session, person.id, [app.id]):
        return RequestResult(Outcome.ALREADY_HAS_ACCOUNT, name)
    if app.id in await apps_with_open_creation(session, person.id, [app.id]):
        return RequestResult(Outcome.ALREADY_REQUESTED, name)

    action = await create_action(
        session,
        ActionCreate(kind=WriteKind.CREATE_ACCOUNT, app_id=app.id, person_id=person.id, role=role),
        reason=ActionReason.SELF_SERVICE,
    )
    note = origin.message if origin else message
    request = AccessRequest(
        person_id=person.id,
        app_id=app.id,
        action_id=action.id,
        channel=AccessRequestChannel.SLACK if origin else AccessRequestChannel.PANEL,
        slack_user_id=origin.user_id if origin else None,
        slack_channel_id=origin.channel_id if origin else None,
        message=(note or "")[:2000] or None,
    )
    session.add(request)
    await session.flush()
    await audit.record(
        session,
        "access_request.created",
        "access_request",
        request.id,
        {"action_id": str(action.id), "policy": str(app.self_service), "channel": str(request.channel)},
        app_id=app.id,
        person_id=person.id,
    )
    if app.self_service != SelfServicePolicy.AUTOMATIC:
        return RequestResult(Outcome.WAITING_FOR_APPROVAL, name, action.id)
    action_id, kind = action.id, action.kind
    try:
        await approve(session, action_id, dispatcher)  # commits; a connector write starts its workflow
    except InvalidInputError as exc:
        return RequestResult(Outcome.WAITING_FOR_APPROVAL, name, action_id, exc.message)
    if kind == ActionKind.MANUAL_TASK:
        return RequestResult(Outcome.WAITING_FOR_ADMIN, name, action_id)
    return RequestResult(Outcome.IN_PROGRESS, name, action_id)


async def list_requests(
    session: AsyncSession, *, status: AccessRequestStatus | None, limit: int, offset: int
) -> AccessRequestPage:
    query = select(AccessRequest)
    if status is not None:
        query = query.where(AccessRequest.status == status)
    total = await session.scalar(select(func.count()).select_from(query.subquery())) or 0
    rows = list(
        await session.scalars(
            query.order_by(AccessRequest.created_at.desc(), AccessRequest.id.desc()).limit(limit).offset(offset)
        )
    )
    people = {p.id: p for p in await session.scalars(select(Person).where(Person.id.in_({r.person_id for r in rows})))}
    apps = {a.id: a for a in await session.scalars(select(App).where(App.id.in_({r.app_id for r in rows})))}
    action_ids = {r.action_id for r in rows if r.action_id}
    statuses = dict((await session.execute(select(Action.id, Action.status).where(Action.id.in_(action_ids)))).all())
    items = [
        AccessRequestOut(
            id=row.id,
            person=person_ref(people[row.person_id]),
            app=app_ref(apps[row.app_id]),
            action_id=row.action_id,
            action_status=statuses.get(row.action_id) if row.action_id else None,
            channel=row.channel,
            status=row.status,
            message=row.message,
            created_at=row.created_at,
            closed_at=row.closed_at,
            notified_at=row.notified_at,
        )
        for row in rows
    ]
    return AccessRequestPage(items=items, total=total)


CLOSING_STATUS = {
    ActionStatus.DONE: AccessRequestStatus.DONE,
    ActionStatus.FAILED: AccessRequestStatus.FAILED,
    ActionStatus.CANCELLED: AccessRequestStatus.CANCELLED,
}


def closing_status(action_status: ActionStatus | None) -> AccessRequestStatus:
    """How a request ends for the status of its action; a deleted action counts as cancelled."""
    if action_status is None:
        return AccessRequestStatus.CANCELLED
    return CLOSING_STATUS.get(action_status, AccessRequestStatus.CANCELLED)


def close(request: AccessRequest, status: AccessRequestStatus) -> None:
    request.status = status
    request.closed_at = datetime.now(UTC)
