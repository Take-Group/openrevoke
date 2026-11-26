"""The record of an access request: decisions, audit events and closing.

Shared by the request flow (``flow.py``) and by the action hook (``request_sync.py``); it imports
no action services, so both can use it.
"""

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import select

from app.models import AccessRequest, AccessRequestDecision, Person, User
from app.models.enums import AccessRequestStatus, DecisionOutcome, DecisionStep
from app.services import audit
from app.services.errors import PermissionDeniedError
from app.services.matching import match_email

if TYPE_CHECKING:
    import uuid

    from sqlalchemy.ext.asyncio import AsyncSession

    from app.services.auth.actor import ActorRef

CLOSED_STATUSES = frozenset(
    {AccessRequestStatus.DONE, AccessRequestStatus.FAILED, AccessRequestStatus.REJECTED, AccessRequestStatus.CANCELLED}
)


async def record_decision(
    session: AsyncSession,
    request: AccessRequest,
    *,
    step: DecisionStep,
    outcome: DecisionOutcome,
    decider: ActorRef,
    comment: str | None = None,
    override: bool = False,
) -> AccessRequestDecision:
    """Append a decision and its audit event (``access_request.<step>_<outcome>`` or ``.overridden``)."""
    decision = AccessRequestDecision(
        request_id=request.id,
        step=step,
        decision=outcome,
        decided_by_user_id=decider.user_id,
        decided_by=decider.label[:320],
        via=decider.via,
        override=override,
        comment=(comment or "").strip()[:2000] or None,
    )
    session.add(decision)
    await session.flush()
    event = "access_request.overridden" if override else f"access_request.{step}_{outcome}"
    await record_event(
        session,
        request,
        event,
        {"step": str(step), "decision": str(outcome), "via": str(decider.via), "comment": decision.comment},
    )
    return decision


async def record_event(session: AsyncSession, request: AccessRequest, event: str, data: dict[str, Any]) -> None:
    await audit.record(
        session, event, "access_request", request.id, data, app_id=request.app_id, person_id=request.person_id
    )


def close(request: AccessRequest, status: AccessRequestStatus) -> None:
    request.status = status
    request.closed_at = datetime.now(UTC)


async def person_id_of_user(session: AsyncSession, user_id: uuid.UUID | None) -> uuid.UUID | None:
    """The person a panel user is (by e-mail, primary or alias); None without a user or a person."""
    if user_id is None:
        return None
    user = await session.get(User, user_id)
    return (await match_email(session, user.email)).person_id if user else None


async def ensure_not_own(session: AsyncSession, request: AccessRequest, decider: ActorRef) -> None:
    """Nobody decides their own request. Raises 403."""
    if await person_id_of_user(session, decider.user_id) == request.person_id:
        raise PermissionDeniedError("You cannot decide your own request. Another approver has to.")


async def last_rejection(session: AsyncSession, request_ids: list[uuid.UUID]) -> dict[uuid.UUID, str | None]:
    """The comment of the rejecting decision per request, for requests that were rejected."""
    if not request_ids:
        return {}
    rows = await session.execute(
        select(AccessRequestDecision.request_id, AccessRequestDecision.comment)
        .where(
            AccessRequestDecision.request_id.in_(request_ids),
            AccessRequestDecision.decision == DecisionOutcome.REJECTED,
        )
        .order_by(AccessRequestDecision.decided_at)
    )
    return dict(rows.tuples().all())


async def people_by_id(session: AsyncSession, ids: set[uuid.UUID | None]) -> dict[uuid.UUID, Person]:
    wanted = {i for i in ids if i is not None}
    if not wanted:
        return {}
    return {person.id: person for person in await session.scalars(select(Person).where(Person.id.in_(wanted)))}
