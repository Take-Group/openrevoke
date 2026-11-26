"""Reading actions for the API: the queue with counts per status, and single actions."""

from typing import TYPE_CHECKING

from sqlalchemy import Select, func, or_, select
from sqlalchemy.orm import aliased

from app.models import Account, Action, ActionScreenshot, App, Connection, Person
from app.models.enums import ActionKind, ActionStatus
from app.schemas.actions import ActionOut, ActionPayload
from app.services.capabilities import delete_suspends
from app.services.errors import NotFoundError
from app.services.presenters import account_ref, app_ref, person_ref
from app.services.recipe_fixes import list_fixes

if TYPE_CHECKING:
    import uuid

    from sqlalchemy.ext.asyncio import AsyncSession

_PERSON = aliased(Person)
_ACCOUNT = aliased(Account)

type Row = tuple[Action, App, Person | None, Account | None, Connection | None, uuid.UUID | None]


async def list_actions(
    session: AsyncSession,
    *,
    statuses: list[ActionStatus] | None,
    batch_id: uuid.UUID | None,
    person_id: uuid.UUID | None,
    app_id: uuid.UUID | None,
    q: str | None,
    limit: int,
    offset: int,
) -> tuple[list[ActionOut], int, dict[ActionStatus, int]]:
    """Page of actions, total, and counts per status under the same filters except ``statuses``."""
    query = _joined()
    if batch_id:
        query = query.where(Action.batch_id == batch_id)
    if person_id:
        query = query.where(Action.person_id == person_id)
    if app_id:
        query = query.where(Action.app_id == app_id)
    if q:
        pattern = f"%{q.strip()}%"
        query = query.where(
            or_(
                App.name.ilike(pattern),
                _PERSON.primary_email.ilike(pattern),
                (_PERSON.first_name + " " + _PERSON.last_name).ilike(pattern),
                _ACCOUNT.email.ilike(pattern),
            )
        )
    by_status = query.subquery()
    counts = dict.fromkeys(ActionStatus, 0)
    for status, count in await session.execute(select(by_status.c.status, func.count()).group_by(by_status.c.status)):
        counts[ActionStatus(status)] = count
    if statuses:
        query = query.where(Action.status.in_(statuses))
    total = await session.scalar(select(func.count()).select_from(query.subquery()))
    rows = await session.execute(query.order_by(Action.created_at.desc(), Action.id).limit(limit).offset(offset))
    return await _with_fixes(session, [_out(*row) for row in rows]), total or 0, counts


async def get_actions_out(session: AsyncSession, action_ids: list[uuid.UUID]) -> list[ActionOut]:
    if not action_ids:
        return []
    rows = await session.execute(_joined().where(Action.id.in_(action_ids)).order_by(Action.created_at, Action.id))
    by_id = {row[0].id: _out(*row) for row in rows}
    return await _with_fixes(session, [by_id[action_id] for action_id in action_ids if action_id in by_id])


async def get_action_out(session: AsyncSession, action_id: uuid.UUID) -> ActionOut:
    items = await get_actions_out(session, [action_id])
    if not items:
        raise NotFoundError("Action not found")
    return items[0]


async def screenshot(session: AsyncSession, action_id: uuid.UUID) -> bytes:
    """PNG of the tab where the action's click recipe stopped."""
    row = await session.get(ActionScreenshot, action_id)
    if row is None:
        raise NotFoundError("This action has no screenshot")
    return row.png


def _joined() -> Select[Row]:
    return (
        select(Action, App, _PERSON, _ACCOUNT, Connection, ActionScreenshot.action_id)
        .join(App, App.id == Action.app_id)
        .outerjoin(_PERSON, _PERSON.id == Action.person_id)
        .outerjoin(_ACCOUNT, _ACCOUNT.id == Action.account_id)
        .outerjoin(Connection, Connection.app_id == Action.app_id)
        .outerjoin(ActionScreenshot, ActionScreenshot.action_id == Action.id)
    )


async def _with_fixes(session: AsyncSession, items: list[ActionOut]) -> list[ActionOut]:
    fixes = await list_fixes(session, action_ids=[item.id for item in items])
    for item in items:
        item.recipe_fixes = [fix for fix in fixes if fix.action_id == item.id]
    return items


def _out(
    action: Action,
    app: App,
    person: Person | None,
    account: Account | None,
    conn: Connection | None,
    screenshot_id: uuid.UUID | None,
) -> ActionOut:
    return ActionOut(
        id=action.id,
        kind=action.kind,
        status=action.status,
        reason=action.reason,
        batch_id=action.batch_id,
        person=person_ref(person),
        app=app_ref(app),
        account=account_ref(account),
        payload=ActionPayload.model_validate(action.payload or {}),
        approved_at=action.approved_at,
        approved_by=action.approved_by,
        created_by=action.created_by,
        started_at=action.started_at,
        finished_at=action.finished_at,
        result=action.result,
        error=action.error,
        has_secret_result=action.secret_result_encrypted is not None,
        suspends=action.kind == ActionKind.DELETE_ACCOUNT and delete_suspends(conn),
        has_screenshot=screenshot_id is not None,
        created_at=action.created_at,
    )
