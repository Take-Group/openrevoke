"""The signed-in user's own access: their accounts, their requests, apps they may ask for, and their team.

The user is tied to a ``Person`` by e-mail (primary or alias, ``matching.match_email``). Self sign-up
proves the e-mail with a link (``auth/signup.py``), so a user only ever sees their own accounts. A
manager (a person others have as ``manager_id``) also sees their reports and may ask for them.
"""

from typing import TYPE_CHECKING

from sqlalchemy import func, select

from app.models import AccessRequest, Account, App, Person
from app.models.enums import OPEN_REQUEST_STATUSES, AccountStatus, PersonStatus, RequestPolicy
from app.schemas.me import (
    MyAccess,
    MyAccessRequestResult,
    MyAccount,
    MyRequest,
    MyTeam,
    RequestableApp,
    TeamMember,
)
from app.services.access import queries
from app.services.access.requests import NewRequest, request_access
from app.services.auth.actor import current_actor
from app.services.errors import InvalidInputError, NotFoundError, PermissionDeniedError
from app.services.matching import match_email
from app.services.onboarding import apps_with_open_creation
from app.services.presenters import app_ref, person_ref

if TYPE_CHECKING:
    import uuid

    from sqlalchemy.ext.asyncio import AsyncSession

    from app.models import User
    from app.schemas.me import MyAccessRequestCreate
    from app.services.action_dispatch import ActionDispatcher

REQUEST_LIMIT = 50
ROLE_SUGGESTIONS = 20
NOT_LISTED = "Your e-mail is not on the company's people list yet. Ask an admin to add you."


async def person_of(session: AsyncSession, user: User) -> Person | None:
    person_id = (await match_email(session, user.email)).person_id
    return await session.get(Person, person_id) if person_id else None


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
    rows = list(
        await session.scalars(
            select(AccessRequest)
            .where(AccessRequest.person_id == person.id)
            .order_by(AccessRequest.created_at.desc())
            .limit(REQUEST_LIMIT)
        )
    )
    requests = [
        MyRequest(
            request_id=out.id,
            app=out.app,
            status=out.status,
            waiting_for=out.waiting_for,
            approver=out.approver,
            fallback_reason=out.fallback_reason,
            justification=out.justification,
            role=out.role,
            rejection_comment=out.rejection_comment,
            requested_by=out.requested_by,
            on_behalf=out.on_behalf,
            created_at=out.created_at,
            closed_at=out.closed_at,
        )
        for out in await queries.present(session, rows)
    ]
    return MyAccess(
        person=person_ref(person),
        accounts=accounts,
        requests=requests,
        requestable_apps=await requestable(session, person, {app.id for _, app in account_rows}),
    )


async def requestable(session: AsyncSession, person: Person, with_account: set[uuid.UUID]) -> list[RequestableApp]:
    """Apps the person can ask for: policy not off, no account, no open request or creation."""
    if person.status == PersonStatus.LEFT:
        return []
    apps = list(await session.scalars(select(App).where(App.request_policy != RequestPolicy.OFF).order_by(App.name)))
    candidates = [app for app in apps if app.id not in with_account]
    ids = [app.id for app in candidates]
    busy = await apps_with_open_creation(session, person.id, ids)
    busy |= set(
        await session.scalars(
            select(AccessRequest.app_id).where(
                AccessRequest.person_id == person.id, AccessRequest.status.in_(OPEN_REQUEST_STATUSES)
            )
        )
    )
    roles = await _roles(session, ids)
    return [
        RequestableApp(app=app_ref(app), policy=app.request_policy, roles=roles.get(app.id, []))
        for app in candidates
        if app.id not in busy
    ]


async def _roles(session: AsyncSession, app_ids: list[uuid.UUID]) -> dict[uuid.UUID, list[str]]:
    rows = await session.execute(
        select(Account.app_id, Account.role)
        .where(Account.app_id.in_(app_ids), Account.role.is_not(None), Account.status != AccountStatus.REMOVED)
        .group_by(Account.app_id, Account.role)
        .order_by(Account.app_id, func.count().desc(), Account.role)
    )
    roles: dict[uuid.UUID, list[str]] = {}
    for app_id, role in rows.tuples():
        if role and len(roles.setdefault(app_id, [])) < ROLE_SUGGESTIONS:
            roles[app_id].append(role)
    return roles


async def request(
    session: AsyncSession, user: User, data: MyAccessRequestCreate, *, dispatcher: ActionDispatcher
) -> MyAccessRequestResult:
    """Ask for an account for yourself or, as their manager, for a report. 403: not your report."""
    me = await person_of(session, user)
    if me is None:
        raise InvalidInputError(NOT_LISTED)
    person = me
    if data.person_id is not None and data.person_id != me.id:
        report = await session.get(Person, data.person_id)
        if report is None or report.manager_id != me.id:
            raise PermissionDeniedError("You can ask only for yourself or for people whose manager you are.")
        person = report
    app = await session.get(App, data.app_id)
    if app is None:
        raise NotFoundError("App not found.")
    new = NewRequest(
        justification=data.justification,
        requested_by=current_actor.get(),
        role=data.role,
        on_behalf=person.id != me.id,
    )
    result = await request_access(session, person=person, app=app, new=new, dispatcher=dispatcher)
    await session.commit()  # before the response: the next call (an approval) must see the request
    return MyAccessRequestResult(
        outcome=str(result.outcome), app_name=result.app_name, note=result.note, request_id=result.request_id
    )


async def team(session: AsyncSession, user: User) -> MyTeam:
    """The user's reports with their apps and the apps the user can ask for on their behalf."""
    me = await person_of(session, user)
    if me is None:
        return MyTeam(reports=[])
    reports = list(
        await session.scalars(
            select(Person)
            .where(Person.manager_id == me.id, Person.id != me.id, Person.status != PersonStatus.LEFT)
            .order_by(Person.first_name, Person.last_name)
        )
    )
    members = []
    for report in reports:
        apps = list(
            await session.scalars(
                select(App)
                .join(Account, Account.app_id == App.id)
                .where(Account.person_id == report.id, Account.status != AccountStatus.REMOVED)
                .distinct()
                .order_by(App.name)
            )
        )
        person = person_ref(report)
        assert person is not None
        members.append(
            TeamMember(
                person=person,
                apps=[app_ref(app) for app in apps],
                requestable_apps=await requestable(session, report, {app.id for app in apps}),
            )
        )
    return MyTeam(reports=members)
