"""Approval: a person approves, a connector write starts ``ExecuteActionWorkflow`` at once.

Rules:

- a connector write is approved only when its connection allows writes
  (``writes_enabled``); otherwise 400 and the action stays pending,
- a manual task is approved and waits for a person to close it,
- a batch (offboarding) approves what it can and lists the rest,
- the one-time secret of a create (temporary password) is shown once.
"""

from typing import TYPE_CHECKING

import structlog
from sqlalchemy import select

from app.models import Action, App, Connection
from app.models.enums import ActionKind, ActionStatus
from app.schemas.actions import ActionSecret, WriteKind
from app.services import audit
from app.services.actions import advance, can_transition, get_action
from app.services.capabilities import connector_supports
from app.services.errors import ConflictError, InvalidInputError, NotFoundError
from app.services.secret_box import SecretsUnreadableError, decrypt_value

if TYPE_CHECKING:
    import uuid

    from sqlalchemy.ext.asyncio import AsyncSession

    from app.services.action_dispatch import ActionDispatcher
    from app.services.auth.actor import ActorRef

logger = structlog.get_logger()
S = ActionStatus


async def approve(
    session: AsyncSession, action_id: uuid.UUID, dispatcher: ActionDispatcher, *, approved_by: ActorRef | None = None
) -> None:
    """``approved_by``: who the action names as approver; default the current actor (the signed-in user)."""
    # Row lock until the commit: a second approval waits, then sees "approved" and gets 409.
    action = await get_action(session, action_id, lock=True)
    if not can_transition(action, S.APPROVED):
        raise ConflictError(f"Only a pending action can be approved (this one is {action.status})")
    if action.kind != ActionKind.MANUAL_TASK:
        await ensure_can_run(session, action)
    await advance(session, action.id, S.APPROVED, approved_by=approved_by)
    if action.kind != ActionKind.MANUAL_TASK:
        await session.commit()  # the worker reads the approved action
        await start_workflow(session, action, dispatcher)
        session.expire_all()  # the workflow may already have moved it on


async def approve_batch(
    session: AsyncSession, batch_id: uuid.UUID, dispatcher: ActionDispatcher
) -> tuple[list[uuid.UUID], list[tuple[uuid.UUID, str]]]:
    """Approve every pending action of the batch that may run. Returns (approved ids, refused ids with reason)."""
    actions = list(
        await session.scalars(
            select(Action)
            .where(Action.batch_id == batch_id)
            .order_by(Action.created_at, Action.id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
    )
    if not actions:
        raise NotFoundError("Batch not found")
    approved: list[Action] = []
    refused: list[tuple[uuid.UUID, str]] = []
    for action in actions:
        if action.status != S.PENDING_APPROVAL:
            continue
        if action.kind != ActionKind.MANUAL_TASK:
            try:
                await ensure_can_run(session, action)
            except InvalidInputError as exc:
                refused.append((action.id, exc.message))
                continue
        approved.append(await advance(session, action.id, S.APPROVED))
    await session.commit()
    # One workflow per write; writes on one connection wait for each other (connection lock).
    for action in approved:
        if action.kind != ActionKind.MANUAL_TASK:
            await start_workflow(session, action, dispatcher)
    approved_ids = [action.id for action in approved]
    session.expire_all()  # the workflows may already have moved them on
    return approved_ids, refused


async def ensure_can_run(session: AsyncSession, action: Action) -> None:
    """A connector write runs only through a connector that can do it, with writes enabled. Raises 400."""
    app = await session.get(App, action.app_id)
    connection = await session.scalar(select(Connection).where(Connection.app_id == action.app_id))
    name = app.name if app else "The app"
    if not connector_supports(connection, WriteKind(str(action.kind))):
        raise InvalidInputError(
            f"{name} has no connector that can do {action.kind} anymore. Cancel this action and create it again"
        )
    assert connection is not None
    if not connection.writes_enabled:
        raise InvalidInputError(
            f"Writes are disabled for {name}. Turn on 'Allow writes' in the app's connection settings, "
            "then approve again"
        )


async def reveal_secret(session: AsyncSession, action_id: uuid.UUID) -> ActionSecret:
    """Return the stored one-time secret and wipe it. The audit event never contains the value."""
    action = await session.scalar(select(Action).where(Action.id == action_id).with_for_update())
    if action is None:
        raise NotFoundError("Action not found")
    if action.secret_result_encrypted is None:
        raise NotFoundError("This action has no secret to show. A secret is shown only once")
    try:
        value = decrypt_value(action.secret_result_encrypted)
    except SecretsUnreadableError as exc:
        raise ConflictError("The secret cannot be decrypted: OPEN_REVOKE_SECRET_KEY has changed") from exc
    kind = str((action.result or {}).get("secret_kind") or "temporary_password")
    action.secret_result_encrypted = None
    await session.flush()
    await audit.record(session, "action.secret_revealed", "action", action.id, {"kind": kind})
    return ActionSecret(kind=kind, value=value)


async def start_workflow(
    session: AsyncSession, action: Action, dispatcher: ActionDispatcher, *, retry: int = 0
) -> None:
    """Start the workflow of an approved, committed write; a start failure ends the action as ``failed``."""
    try:
        await dispatcher.start_action(action.id, retry=retry)
    except Exception as exc:  # noqa: BLE001 - shown on the action instead of a 500
        logger.warning("action_start_failed", action_id=str(action.id), error=str(exc))
        await advance(session, action.id, S.FAILED, error=f"Could not start the action workflow: {exc}")
        await session.commit()
