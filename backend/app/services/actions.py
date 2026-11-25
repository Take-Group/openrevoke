"""Actions: creation and status transitions.

Approval and the start of ``ExecuteActionWorkflow`` are in
``action_approval.py``, the steps of the workflow in ``action_execution.py``,
reading for the API in ``action_queries.py``. Lifecycle:
``skills/backend/actions.md``.
"""

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import select

from app.models import Account, Action, App, Connection, Person
from app.models.enums import AccountStatus, ActionKind, ActionReason, ActionStatus
from app.schemas.actions import ActionCreate, WriteKind
from app.services import audit
from app.services.action_accounts import add_manual_account
from app.services.capabilities import connector_supports
from app.services.errors import ConflictError, InvalidInputError, NotFoundError
from app.services.matching import is_valid_email, normalize_email

if TYPE_CHECKING:
    import uuid

    from sqlalchemy.ext.asyncio import AsyncSession

S = ActionStatus
TRANSITIONS: dict[ActionStatus, frozenset[ActionStatus]] = {
    S.PENDING_APPROVAL: frozenset({S.APPROVED, S.CANCELLED, S.DONE}),
    S.APPROVED: frozenset({S.RUNNING, S.CANCELLED, S.DONE, S.FAILED}),
    S.RUNNING: frozenset({S.VERIFYING, S.DONE, S.FAILED}),
    S.VERIFYING: frozenset({S.DONE, S.FAILED}),
    S.FAILED: frozenset({S.CANCELLED, S.APPROVED}),  # approved again: a retry or a manual task (action_retry)
    S.DONE: frozenset(),
    S.CANCELLED: frozenset(),
}
OPEN_STATUSES = frozenset({S.PENDING_APPROVAL, S.APPROVED, S.RUNNING, S.VERIFYING})
FINISHED_STATUSES = frozenset({S.DONE, S.FAILED, S.CANCELLED})


def can_transition(action: Action, target: ActionStatus) -> bool:
    if target not in TRANSITIONS[action.status]:
        return False
    # Only a person closes a manual task as done before it runs; connector writes are confirmed by a read.
    if target == S.DONE and action.status in {S.PENDING_APPROVAL, S.APPROVED}:
        return action.kind == ActionKind.MANUAL_TASK
    return not (action.kind == ActionKind.MANUAL_TASK and target in {S.RUNNING, S.VERIFYING})


def apply_transition(action: Action, target: ActionStatus, now: datetime | None = None) -> None:
    """Move the action to ``target`` and stamp the matching timestamps. Raises ConflictError."""
    if not can_transition(action, target):
        raise ConflictError(f"Action {action.kind} cannot go from {action.status} to {target}")
    now = now or datetime.now(UTC)
    if target == S.APPROVED or (target == S.DONE and action.approved_at is None):
        action.approved_at = now
    if target == S.RUNNING:
        action.started_at = now
    if target in FINISHED_STATUSES:
        action.finished_at = now
    action.status = target


async def create_action(
    session: AsyncSession,
    data: ActionCreate,
    *,
    reason: ActionReason = ActionReason.MANUAL,
    batch_id: uuid.UUID | None = None,
) -> Action:
    app = await session.get(App, data.app_id)
    if app is None:
        raise InvalidInputError("App not found")
    person = await session.get(Person, data.person_id) if data.person_id else None
    if data.person_id and person is None:
        raise InvalidInputError("Person not found")
    account = await session.get(Account, data.account_id) if data.account_id else None
    if data.account_id and (account is None or account.app_id != app.id):
        raise InvalidInputError("Account not found in this app")

    payload: dict[str, Any] = {"role": (data.role or "").strip() or None}
    if data.kind == WriteKind.DELETE_ACCOUNT:
        if account is None:
            raise InvalidInputError("delete_account needs account_id")
        if account.status == AccountStatus.REMOVED:
            raise ConflictError("The account is already removed")
        person = person or (await session.get(Person, account.person_id) if account.person_id else None)
        payload["email"] = account.email
        payload["role"] = payload["role"] or account.role
    else:
        if person is None:
            raise InvalidInputError("create_account needs person_id")
        email = normalize_email(data.email) or person.primary_email
        if not is_valid_email(email):
            raise InvalidInputError(f"Invalid email: {data.email!r}")
        payload["email"] = email

    connection = await session.scalar(select(Connection).where(Connection.app_id == app.id))
    kind = ActionKind(data.kind) if connector_supports(connection, data.kind) else ActionKind.MANUAL_TASK
    if kind == ActionKind.MANUAL_TASK:
        payload["operation"] = str(data.kind)
    action = Action(
        kind=kind,
        person_id=person.id if person else None,
        app_id=app.id,
        account_id=account.id if account else None,
        payload=payload,
        status=S.PENDING_APPROVAL,
        reason=reason,
        batch_id=batch_id,
    )
    session.add(action)
    await session.flush()
    await audit.record(
        session,
        "action.created",
        "action",
        action.id,
        {"kind": str(kind), "reason": str(reason), "batch_id": _str(batch_id), "payload": payload},
    )
    return action


async def advance(
    session: AsyncSession,
    action_id: uuid.UUID,
    target: ActionStatus,
    *,
    result: dict[str, Any] | None = None,
    error: str | None = None,
    data: dict[str, Any] | None = None,
) -> Action:
    """Transition with audit (``action.<target>``); ``data`` goes to the audit event.

    The row is locked (``SELECT ... FOR UPDATE``) and re-read, so two requests or a request and
    the workflow never move the same action from the same status twice (e.g. a double approval).
    """
    action = await get_action(session, action_id, lock=True)
    apply_transition(action, target)
    if result is not None:
        action.result = result
    if error is not None:
        action.error = error
    await session.flush()
    event_data = {**(data or {}), **({"error": error} if error else {})}
    await audit.record(session, f"action.{target}", "action", action.id, event_data or None)
    if target == S.DONE:
        await _close_manual_task(session, action)
    return action


async def cancel(session: AsyncSession, action_id: uuid.UUID) -> Action:
    return await advance(session, action_id, S.CANCELLED)


async def complete(session: AsyncSession, action_id: uuid.UUID) -> Action:
    action = await get_action(session, action_id)
    if action.kind != ActionKind.MANUAL_TASK:
        raise ConflictError("Only a manual task is completed by hand")
    return await advance(session, action_id, S.DONE)


async def _close_manual_task(session: AsyncSession, action: Action) -> None:
    """A done manual task changes accounts no sync will ever check.

    Deletion: an account without a connection becomes ``removed``. Creation in an
    app without a connection: the account is added and assigned to the person.
    With a connection, the next sync confirms the change instead.
    """
    if action.kind != ActionKind.MANUAL_TASK:
        return
    operation = action.payload.get("operation")
    if operation == WriteKind.CREATE_ACCOUNT:
        has_connection = await session.scalar(select(Connection.id).where(Connection.app_id == action.app_id))
        if has_connection is None:
            await add_manual_account(session, action)
        return
    if operation != WriteKind.DELETE_ACCOUNT:
        return
    account = await session.get(Account, action.account_id) if action.account_id else None
    if account is None or account.connection_id is not None or account.status == AccountStatus.REMOVED:
        return
    account.status = AccountStatus.REMOVED
    account.removed_at = datetime.now(UTC)
    await session.flush()
    await audit.record(session, "account.removed", "account", account.id, {"action_id": str(action.id)})


async def get_action(session: AsyncSession, action_id: uuid.UUID, *, lock: bool = False) -> Action:
    """``lock=True`` takes a row lock until the transaction ends and reloads the row from the database."""
    action = await session.get(Action, action_id, with_for_update=lock, populate_existing=lock)
    if action is None:
        raise NotFoundError("Action not found")
    return action


def _str(value: object) -> str | None:
    return None if value is None else str(value)
