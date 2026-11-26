"""The signed-in user's own access: their accounts, their requests, and apps they may ask for.

The user is tied to a ``Person`` by e-mail (primary or alias, ``matching.match_email``). Self sign-up
proves the e-mail with a link (``auth/signup.py``), so a user only ever sees their own accounts.
"""

from typing import TYPE_CHECKING

from sqlalchemy import select

from app.models import AccessRequest, Account, Action, App, Person
from app.models.enums import AccountStatus, ActionStatus, PersonStatus, RequestPolicy
from app.schemas.me import (
    MyAccess,
    MyAccessRequestResult,
    MyAccount,
    MyRequest,
    RequestableApp,
    RequestState,
)
from app.services.access.requests import request_access
from app.services.errors import InvalidInputError, NotFoundError
from app.services.matching import match_email
from app.services.onboarding import apps_with_open_creation
from app.services.presenters import app_ref, person_ref

if TYPE_CHECKING:
    import uuid

    from sqlalchemy.ext.asyncio import AsyncSession

    from app.models import User
    from app.services.action_dispatch import ActionDispatcher

REQUEST_LIMIT = 50
STATE_OF_ACTION = {
    ActionStatus.PENDING_APPROVAL: RequestState.WAITING_FOR_APPROVAL,
    ActionStatus.DONE: RequestState.DONE,
    ActionStatus.FAILED: RequestState.FAILED,
    ActionStatus.CANCELLED: RequestState.CANCELLED,
}
NOT_LISTED = "Your e-mail is not on the company's people list yet. Ask an admin to add you."


async def person_of(session: AsyncSession, user: User) -> Person | None:
    person_id = (await match_email(session, user.email)).person_id
    return await session.get(Person, person_id) if person_id else None


def _state(action_status: ActionStatus | None) -> RequestState:
    if action_status is None:
        return RequestState.CANCELLED  # the action was deleted
    return STATE_OF_ACTION.get(action_status, RequestState.IN_PROGRESS)


async def overview(session: AsyncSession, user: User) -> MyAccess:
    person = await person_of(session, user)
    if person is None:
        return MyAccess(person=None, accounts=[], requests=[], requestable_apps=[])
    account_rows = (
        await session.execute(
            select(Account, App)
            .join(App, App.id == Account.app_id)
            .where(Account.person_id == person.id, Account.status != AccountStatus.REMOVED)
            .order_by(App.name, Account.email)
        )
    ).all()
    accounts = [
        MyAccount(
            account_id=account.id,
            app=app_ref(app),
            email=account.email,
            username=account.username,
            role=account.role,
            status=account.status,
            first_seen_at=account.first_seen_at,
            last_seen_at=account.last_seen_at,
        )
        for account, app in account_rows
    ]
    request_rows = (
        await session.execute(
            select(AccessRequest, App, Action.status)
            .join(App, App.id == AccessRequest.app_id)
            .outerjoin(Action, Action.id == AccessRequest.action_id)
            .where(AccessRequest.person_id == person.id)
            .order_by(AccessRequest.created_at.desc())
            .limit(REQUEST_LIMIT)
        )
    ).all()
    requests = [
        MyRequest(
            request_id=request.id,
            app=app_ref(app),
            state=_state(action_status),
            message=request.message,
            created_at=request.created_at,
        )
        for request, app, action_status in request_rows
    ]
    return MyAccess(
        person=person_ref(person),
        accounts=accounts,
        requests=requests,
        requestable_apps=await _requestable(session, person, {app.id for _, app in account_rows}),
    )


async def _requestable(session: AsyncSession, person: Person, with_account: set[uuid.UUID]) -> list[RequestableApp]:
    if person.status == PersonStatus.LEFT:
        return []
    apps = list(await session.scalars(select(App).where(App.request_policy != RequestPolicy.OFF).order_by(App.name)))
    candidates = [app for app in apps if app.id not in with_account]
    requested = await apps_with_open_creation(session, person.id, [app.id for app in candidates])
    return [
        RequestableApp(app=app_ref(app), needs_approval=app.request_policy != RequestPolicy.AUTOMATIC)
        for app in candidates
        if app.id not in requested
    ]


async def request(
    session: AsyncSession,
    user: User,
    *,
    app_id: uuid.UUID,
    message: str | None,
    dispatcher: ActionDispatcher,
) -> MyAccessRequestResult:
    """Ask for an account in an app, with the same rules as the Slack agent (the app's self-service policy)."""
    person = await person_of(session, user)
    if person is None:
        raise InvalidInputError(NOT_LISTED)
    app = await session.get(App, app_id)
    if app is None:
        raise NotFoundError("App not found.")
    result = await request_access(
        session, person=person, app=app, role=None, dispatcher=dispatcher, message=(message or "").strip() or None
    )
    return MyAccessRequestResult(outcome=str(result.outcome), app_name=result.app_name, note=result.note)
