"""The steps of an access request: who decides, what each decision does. Flow in ``skills/backend/access-requests.md``.

``route`` sends a new request to its first step by the app's ``request_policy``:

- ``automatic``: approved at once (decision ``via=automatic``), the action runs;
- ``admin``: the ``create_account`` action waits for an admin (``pending_admin``);
- ``manager`` and ``manager_then_admin``: the person's manager decides (``pending_manager``), unless
  an access profile with ``auto_approve_requests`` holds the app or the manager asked for their report
  (the step is met ``via=automatic``), or no manager can decide (``fallback_reason``, ``pending_admin``).

After the manager's yes the action is created: ``manager`` approves it at once (with the manager as
approver; writes off leave it for an admin), ``manager_then_admin`` leaves it for an admin. ``decide``
takes a decision from the panel, the API or Slack; the admin step through ``/actions`` is in
``request_sync.py``.
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING

from sqlalchemy import select

from app.models import AccessRequest, Action, App, Person
from app.models.enums import (
    AccessRequestStatus,
    ActionKind,
    ActionReason,
    ActionStatus,
    DecisionOutcome,
    DecisionStep,
    DecisionVia,
    PersonStatus,
    RequestFallbackReason,
    RequestPolicy,
)
from app.schemas.actions import ActionCreate, WriteKind
from app.services.access import managers, slack_reach
from app.services.access.decisions import close, record_decision, record_event
from app.services.access.outcomes import Outcome, RequestResult
from app.services.access.profiles import auto_approving_profile
from app.services.action_approval import approve, ensure_can_run
from app.services.actions import cancel, create_action
from app.services.auth.actor import ActorRef
from app.services.errors import ConflictError, InvalidInputError, NotFoundError, PermissionDeniedError

if TYPE_CHECKING:
    import uuid

    from sqlalchemy.ext.asyncio import AsyncSession

    from app.services.action_dispatch import ActionDispatcher

R = AccessRequestStatus
MANAGER_POLICIES = frozenset({RequestPolicy.MANAGER, RequestPolicy.MANAGER_THEN_ADMIN})
POLICY = ActorRef("Automatic (app policy)")
REJECTED_IN_SLACK = "Rejected in Slack."
FALLBACK_NOTE = {
    RequestFallbackReason.NO_MANAGER: "No manager is set, so an admin approves it.",
    RequestFallbackReason.MANAGER_LEFT: "The manager has left, so an admin approves it.",
    RequestFallbackReason.MANAGER_NO_ACCESS: "The manager has no panel account and no Slack, so an admin approves it.",
    RequestFallbackReason.MANAGER_IS_REQUESTER: "The person is their own manager, so an admin approves it.",
}


@dataclass(frozen=True)
class Decider:
    """Who decides: the actor for the record, the person they are, and whether they may act as an admin."""

    actor: ActorRef
    person_id: uuid.UUID | None
    is_admin: bool


async def route(
    session: AsyncSession, request: AccessRequest, person: Person, app: App, dispatcher: ActionDispatcher
) -> RequestResult:
    """Send a new, flushed request to its first step. May commit (an approved write starts its workflow)."""
    if app.request_policy == RequestPolicy.AUTOMATIC:
        await record_decision(
            session, request, step=DecisionStep.ADMIN, outcome=DecisionOutcome.APPROVED, decider=POLICY
        )
        return await _create_action(session, request, person, app, dispatcher, approver=POLICY)
    if app.request_policy not in MANAGER_POLICIES:
        return await _create_action(session, request, person, app, dispatcher, approver=None)
    met = await _manager_step_met(session, request, person, app)
    if met is not None:
        decider = ActorRef(met[0], via=DecisionVia.AUTOMATIC)
        await record_decision(
            session,
            request,
            step=DecisionStep.MANAGER,
            outcome=DecisionOutcome.APPROVED,
            decider=decider,
            comment=met[1],
        )
        return await _after_manager(session, request, person, app, dispatcher, approver=decider)
    manager, fallback = await _manager_who_decides(session, person)
    request.approver_person_id = manager.id if manager else None
    if fallback is not None:
        request.fallback_reason = fallback
        await record_event(session, request, "access_request.escalated", {"fallback_reason": str(fallback)})
        result = await _create_action(session, request, person, app, dispatcher, approver=None)
        return RequestResult(result.outcome, result.app_name, result.action_id, FALLBACK_NOTE[fallback])
    request.status = R.PENDING_MANAGER
    await session.flush()
    assert manager is not None
    return RequestResult(Outcome.WAITING_FOR_MANAGER, app.name, note=f"{manager.first_name} {manager.last_name}")


async def _manager_step_met(
    session: AsyncSession, request: AccessRequest, person: Person, app: App
) -> tuple[str, str] | None:
    """(decider label, comment) when the manager step needs nobody: a profile or the manager asked."""
    profile = await auto_approving_profile(session, person.id, app.id)
    if profile is not None:
        return "Automatic (access profile)", f"Access profile {profile.name}"
    if request.on_behalf:
        return request.requested_by or "The manager", "Requested by the manager"
    return None


async def _manager_who_decides(
    session: AsyncSession, person: Person
) -> tuple[Person | None, RequestFallbackReason | None]:
    manager = await managers.manager_of(session, person)
    if manager is None:
        return None, RequestFallbackReason.NO_MANAGER
    if manager.id == person.id:
        return manager, RequestFallbackReason.MANAGER_IS_REQUESTER
    if manager.status == PersonStatus.LEFT:
        return manager, RequestFallbackReason.MANAGER_LEFT
    if await managers.panel_user_of(session, manager) is not None:
        return manager, None
    if await slack_reach.slack_user_id(session, await managers.emails_of(session, manager)):
        return manager, None
    return manager, RequestFallbackReason.MANAGER_NO_ACCESS


async def _after_manager(
    session: AsyncSession,
    request: AccessRequest,
    person: Person,
    app: App,
    dispatcher: ActionDispatcher,
    *,
    approver: ActorRef,
) -> RequestResult:
    """The manager said yes: ``manager`` runs the action with them as approver, the other policy waits."""
    if app.request_policy == RequestPolicy.MANAGER_THEN_ADMIN:
        return await _create_action(session, request, person, app, dispatcher, approver=None)
    return await _create_action(session, request, person, app, dispatcher, approver=approver)


async def _create_action(
    session: AsyncSession,
    request: AccessRequest,
    person: Person,
    app: App,
    dispatcher: ActionDispatcher | None,
    *,
    approver: ActorRef | None,
) -> RequestResult:
    """Create the account action; ``approver`` set: approve it now (needs ``dispatcher``), else it waits."""
    name = app.name  # approve() below expires the session's objects
    action = await create_action(
        session,
        ActionCreate(kind=WriteKind.CREATE_ACCOUNT, app_id=app.id, person_id=person.id, role=request.role),
        reason=ActionReason.SELF_SERVICE,
        created_by=request.requested_by,
    )
    request.action_id = action.id
    action_id, kind = action.id, action.kind
    if approver is None:
        _wait_for_admin(request)
        await session.flush()
        return RequestResult(Outcome.WAITING_FOR_APPROVAL, name, action_id)
    assert dispatcher is not None
    request.status = R.APPROVED
    await session.flush()
    try:
        await approve(session, action_id, dispatcher, approved_by=approver)  # commits; a write starts its workflow
    except InvalidInputError as exc:  # writes are off: an admin approves after turning them on
        _wait_for_admin(request)
        await session.flush()
        return RequestResult(Outcome.WAITING_FOR_APPROVAL, name, action_id, exc.message)
    if kind == ActionKind.MANUAL_TASK:
        return RequestResult(Outcome.WAITING_FOR_ADMIN, name, action_id)
    return RequestResult(Outcome.IN_PROGRESS, name, action_id)


def _wait_for_admin(request: AccessRequest) -> None:
    request.status = R.PENDING_ADMIN
    request.approvers_notified_at = None  # the admins get the Slack message for this step


async def decide(
    session: AsyncSession,
    request_id: uuid.UUID,
    *,
    decider: Decider,
    outcome: DecisionOutcome,
    comment: str | None,
    dispatcher: ActionDispatcher,
) -> None:
    """One decision on the step the request waits for. 403: not the approver, or one's own request.

    409: the request does not wait for a decision. A rejection needs a comment except from Slack.
    The manager's step: the manager, or an admin deciding for them (``override``). The admin step: an admin.
    """
    request = await session.scalar(select(AccessRequest).where(AccessRequest.id == request_id).with_for_update())
    if request is None:
        raise NotFoundError("Access request not found")
    await refresh_approver(session, request)  # the manager may have changed or left since the request
    if decider.person_id is not None and decider.person_id == request.person_id:
        raise PermissionDeniedError("You cannot decide your own request. Another approver has to.")
    is_manager = decider.person_id is not None and decider.person_id == request.approver_person_id
    if not is_manager and not decider.is_admin:
        raise PermissionDeniedError("Only the person's manager or an admin can decide this request.")
    comment = (comment or "").strip() or None
    if outcome == DecisionOutcome.REJECTED and comment is None:
        if decider.actor.via != DecisionVia.SLACK:
            raise InvalidInputError("Say why you reject it: the comment is shown to the person who asked.")
        comment = REJECTED_IN_SLACK
    if request.status == R.PENDING_MANAGER:
        await _decide_manager_step(session, request, decider, outcome, comment, dispatcher, override=not is_manager)
    elif request.status == R.PENDING_ADMIN and decider.is_admin:
        await _decide_admin_step(session, request, decider, outcome, comment, dispatcher)
    elif request.status == R.PENDING_ADMIN:
        raise ConflictError("The manager's step is already decided. The request now waits for an admin.")
    else:
        raise ConflictError(f"The request is already decided ({request.status}).")


async def _decide_manager_step(
    session: AsyncSession,
    request: AccessRequest,
    decider: Decider,
    outcome: DecisionOutcome,
    comment: str | None,
    dispatcher: ActionDispatcher,
    *,
    override: bool,
) -> None:
    await record_decision(
        session,
        request,
        step=DecisionStep.MANAGER,
        outcome=outcome,
        decider=decider.actor,
        comment=comment,
        override=override,
    )
    if outcome == DecisionOutcome.REJECTED:
        close(request, R.REJECTED)
        return
    person = await session.get(Person, request.person_id)
    app = await session.get(App, request.app_id)
    if person is None or app is None:
        raise NotFoundError("The person or the app of this request is gone")
    if person.status == PersonStatus.LEFT:
        raise InvalidInputError("The person has left the company")
    await _after_manager(session, request, person, app, dispatcher, approver=decider.actor)


async def _decide_admin_step(
    session: AsyncSession,
    request: AccessRequest,
    decider: Decider,
    outcome: DecisionOutcome,
    comment: str | None,
    dispatcher: ActionDispatcher,
) -> None:
    action = await session.get(Action, request.action_id) if request.action_id else None
    if action is None or action.status != ActionStatus.PENDING_APPROVAL:
        raise ConflictError("The request's action no longer waits for approval. Open it in Actions.")
    if outcome == DecisionOutcome.APPROVED and action.kind != ActionKind.MANUAL_TASK:
        await ensure_can_run(session, action)  # 400 before anything is recorded
    await record_decision(
        session, request, step=DecisionStep.ADMIN, outcome=outcome, decider=decider.actor, comment=comment
    )
    if outcome == DecisionOutcome.REJECTED:
        close(request, R.REJECTED)
        await cancel(session, action.id)  # the request is closed: request_sync leaves it alone
        return
    request.status = R.APPROVED
    await session.flush()
    await approve(session, action.id, dispatcher, approved_by=decider.actor)


async def refresh_approver(session: AsyncSession, request: AccessRequest) -> None:
    """A request that waits for a manager follows the person's current manager.

    The manager changed: the new one decides (Slack message again). The manager left or can no longer
    decide: the request goes to an admin with the reason, as a new request would.
    """
    if request.status != R.PENDING_MANAGER:
        return
    person = await session.get(Person, request.person_id)
    app = await session.get(App, request.app_id)
    if person is None or app is None:
        return
    manager, fallback = await _manager_who_decides(session, person)
    new_id = manager.id if manager else None
    if fallback is None and new_id == request.approver_person_id:
        return
    old_id = request.approver_person_id
    request.approver_person_id = new_id
    request.approvers_notified_at = None
    data = {"from": str(old_id) if old_id else None, "to": str(new_id) if new_id else None}
    if fallback is not None:
        request.fallback_reason = fallback
        data["fallback_reason"] = str(fallback)
    await record_event(session, request, "access_request.rerouted", data)
    if fallback is not None:
        await _create_action(session, request, person, app, None, approver=None)
    else:
        await session.flush()


async def reroute_pending(session: AsyncSession) -> None:
    """Re-check every request that waits for a manager, after managers or people changed."""
    rows = await session.scalars(
        select(AccessRequest).where(AccessRequest.status == R.PENDING_MANAGER).with_for_update(skip_locked=True)
    )
    for request in list(rows):
        await refresh_approver(session, request)
