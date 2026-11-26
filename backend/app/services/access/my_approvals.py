"""``/api/me/approvals``: requests a manager decides, as a plain panel ``user``.

A user sees a request when it waits (or waited) for them as manager (``approver_person_id``) or when
the person who asked is one of their reports; anything else is 403. Deciding goes through
``flow.decide`` with ``is_admin=False``: only the manager's own step, never an admin's.
"""

from typing import TYPE_CHECKING

from sqlalchemy import exists, select

from app.models import Person
from app.models.enums import AccessRequestStatus
from app.schemas.access_requests import MyApprovals
from app.services.access import flow, queries
from app.services.access.my_access import person_of
from app.services.auth.actor import actor_ref
from app.services.errors import PermissionDeniedError

if TYPE_CHECKING:
    import uuid

    from sqlalchemy.ext.asyncio import AsyncSession

    from app.models import User
    from app.models.enums import DecisionOutcome
    from app.schemas.access_requests import AccessRequestDetail
    from app.services.action_dispatch import ActionDispatcher

NOT_YOURS = "This request is not for you to see: you are not the manager of the person who asked."


async def list_mine(
    session: AsyncSession, user: User, *, statuses: list[AccessRequestStatus] | None, limit: int, offset: int
) -> MyApprovals:
    me = await person_of(session, user)
    if me is None:
        return MyApprovals(items=[], total=0, pending=0, has_reports=False)
    page = await queries.list_requests(
        session, queries.RequestFilter(statuses=statuses, approver_person_id=me.id), limit=limit, offset=offset
    )
    pending = await queries.count(
        session,
        queries.RequestFilter(statuses=[AccessRequestStatus.PENDING_MANAGER], approver_person_id=me.id),
    )
    has_reports = bool(await session.scalar(select(exists().where(Person.manager_id == me.id, Person.id != me.id))))
    return MyApprovals(items=page.items, total=page.total, pending=pending, has_reports=has_reports)


async def detail(session: AsyncSession, user: User, request_id: uuid.UUID) -> AccessRequestDetail:
    me = await _me(session, user)
    request = await queries.get_request(session, request_id)
    if request.approver_person_id != me.id:
        person = await session.get(Person, request.person_id)
        if person is None or person.manager_id != me.id or person.id == me.id:
            raise PermissionDeniedError(NOT_YOURS)
    return await queries.detail(session, request_id)


async def decide(
    session: AsyncSession,
    user: User,
    request_id: uuid.UUID,
    *,
    outcome: DecisionOutcome,
    comment: str | None,
    dispatcher: ActionDispatcher,
) -> AccessRequestDetail:
    me = await _me(session, user)
    decider = flow.Decider(actor=actor_ref(), person_id=me.id, is_admin=False)
    await flow.decide(session, request_id, decider=decider, outcome=outcome, comment=comment, dispatcher=dispatcher)
    await session.commit()
    return await queries.detail(session, request_id)


async def _me(session: AsyncSession, user: User) -> Person:
    me = await person_of(session, user)
    if me is None:
        raise PermissionDeniedError(NOT_YOURS)
    return me
