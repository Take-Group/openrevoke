"""An access request follows its action: ``actions.advance`` calls ``on_action_changed`` on every move.

- approved (or a manual task closed as done) while the request waits for an admin: the admin
  step is decided by whoever approved (``/actions``, ``/requests``, Slack); nobody approves their
  own request (403);
- cancelled while waiting for an admin: ``rejected`` with an admin decision; cancelled later:
  ``cancelled``;
- done or failed: the request closes the same way (the Slack agent then tells the person);
- a retry or "do it by hand" of a failed action opens the request again (``approved``).

Requests the flow already decided (``flow.py`` records the decision first) are left alone here.
"""

from typing import TYPE_CHECKING

from sqlalchemy import select

from app.models import AccessRequest
from app.models.enums import AccessRequestStatus, ActionStatus, DecisionOutcome, DecisionStep
from app.services.access.decisions import close, ensure_not_own, record_decision, record_event
from app.services.auth.actor import actor_ref

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from app.models import Action
    from app.services.auth.actor import ActorRef

R = AccessRequestStatus
CANCELLED_COMMENT = "The action was cancelled."


async def on_action_changed(
    session: AsyncSession, action: Action, previous: ActionStatus, approver: ActorRef | None
) -> None:
    request = await session.scalar(
        select(AccessRequest).where(AccessRequest.action_id == action.id).with_for_update().limit(1)
    )
    if request is None:
        return
    target = action.status
    approved_now = target == ActionStatus.APPROVED or (
        target == ActionStatus.DONE and previous == ActionStatus.PENDING_APPROVAL
    )
    if approved_now and request.status == R.PENDING_ADMIN:
        decider = approver or actor_ref()
        await ensure_not_own(session, request, decider)
        await record_decision(
            session, request, step=DecisionStep.ADMIN, outcome=DecisionOutcome.APPROVED, decider=decider
        )
        request.status = R.APPROVED
    elif target == ActionStatus.APPROVED and request.status == R.FAILED:  # a retry
        request.status, request.closed_at, request.notified_at = R.APPROVED, None, None
        await record_event(session, request, "access_request.reopened", {"action_id": str(action.id)})
    if target == ActionStatus.CANCELLED:
        await _cancelled(session, request)
    elif target in (ActionStatus.DONE, ActionStatus.FAILED) and request.status == R.APPROVED:
        close(request, R.DONE if target == ActionStatus.DONE else R.FAILED)
        await record_event(session, request, "access_request.closed", {"status": str(request.status)})
    await session.flush()


async def _cancelled(session: AsyncSession, request: AccessRequest) -> None:
    if request.status == R.PENDING_ADMIN:
        decider = actor_ref()
        await record_decision(
            session,
            request,
            step=DecisionStep.ADMIN,
            outcome=DecisionOutcome.REJECTED,
            decider=decider,
            comment=CANCELLED_COMMENT,
        )
        close(request, R.REJECTED)
    elif request.status in (R.APPROVED, R.FAILED):
        close(request, R.CANCELLED)
        await record_event(session, request, "access_request.cancelled", {"action_id": str(request.action_id)})
