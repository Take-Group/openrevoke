"""A failed connector write: retry it, or hand it to a person as a manual task.

- ``retry``: ``failed`` to ``approved`` and a new ``ExecuteActionWorkflow``
  run that reads before it writes (``action_execution.precheck``), so a write
  that went through before the failure is not repeated. Same checks as an
  approval (writes enabled, a connector that can do it).
- ``do_by_hand``: the action becomes an approved ``manual_task`` with the same
  operation. The error and the screenshot stay as a hint for the person.
"""

from typing import TYPE_CHECKING

from sqlalchemy import delete

from app.models import ActionScreenshot
from app.models.enums import ActionKind, ActionStatus
from app.services.action_approval import ensure_can_run, start_workflow
from app.services.actions import advance, get_action
from app.services.errors import ConflictError

if TYPE_CHECKING:
    import uuid

    from sqlalchemy.ext.asyncio import AsyncSession

    from app.models import Action
    from app.services.action_dispatch import ActionDispatcher

S = ActionStatus


async def retry(session: AsyncSession, action_id: uuid.UUID, dispatcher: ActionDispatcher) -> None:
    action = await _failed_write(session, action_id, "retried")
    await ensure_can_run(session, action)
    attempt = int((action.result or {}).get("retries", 0)) + 1
    previous = action.error
    await advance(
        session, action.id, S.APPROVED, result={"retries": attempt}, data={"retry": attempt, "previous_error": previous}
    )
    action.error = None
    action.started_at = None
    action.finished_at = None
    await session.execute(delete(ActionScreenshot).where(ActionScreenshot.action_id == action.id))
    await session.commit()  # the worker reads the approved action
    await start_workflow(session, action, dispatcher, retry=attempt)
    session.expire_all()  # the workflow may already have moved it on


async def do_by_hand(session: AsyncSession, action_id: uuid.UUID) -> None:
    action = await _failed_write(session, action_id, "handed to a person")
    operation = str(action.kind)
    action.kind = ActionKind.MANUAL_TASK
    action.payload = {**(action.payload or {}), "operation": operation}
    await advance(session, action.id, S.APPROVED, data={"manual": True, "previous_error": action.error})
    action.finished_at = None


async def _failed_write(session: AsyncSession, action_id: uuid.UUID, verb: str) -> Action:
    action = await get_action(session, action_id, lock=True)
    if action.status != S.FAILED or action.kind == ActionKind.MANUAL_TASK:
        raise ConflictError(f"Only a failed connector write can be {verb} (this one is {action.status})")
    return action
