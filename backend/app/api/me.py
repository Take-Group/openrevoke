"""``/api/me``: the signed-in user's own access and the requests they decide as a manager.

The only panel API a ``user`` (not admin) can call. Approvals show only requests that wait (or
waited) for the user as manager or come from their reports; anything else is 403.
"""

import uuid
from typing import Annotated

from fastapi import APIRouter, Query, status

from app.api.auth_deps import CurrentUserDep
from app.api.deps import ActionDispatcherDep, SessionDep
from app.api.params import Limit, Offset
from app.models.enums import AccessRequestStatus, DecisionOutcome
from app.schemas.access_requests import AccessRequestDecisionCreate, AccessRequestDetail, MyApprovals
from app.schemas.me import MyAccess, MyAccessRequestCreate, MyAccessRequestResult, MyTeam
from app.services.access import my_access, my_approvals

router = APIRouter(prefix="/me")


@router.get("/access", response_model=MyAccess)
async def get_my_access(session: SessionDep, user: CurrentUserDep) -> MyAccess:
    """The signed-in user's own accounts, requests (with status, who decides next, rejection comment) and the
    apps they can ask for."""
    return await my_access.overview(session, user)


@router.post("/access-requests", response_model=MyAccessRequestResult, status_code=status.HTTP_201_CREATED)
async def request_my_access(
    data: MyAccessRequestCreate, session: SessionDep, user: CurrentUserDep, dispatcher: ActionDispatcherDep
) -> MyAccessRequestResult:
    """Ask for an account in an app, for yourself or (``person_id``) for one of your reports.

    The app's request policy decides who approves: the manager, an admin, both, or nobody. 400 without a
    justification, 403 for someone who is not your report, 409 when a request for the app is already open."""
    return await my_access.request(session, user, data, dispatcher=dispatcher)


@router.get("/team", response_model=MyTeam)
async def get_my_team(session: SessionDep, user: CurrentUserDep) -> MyTeam:
    """People whose manager is the signed-in user, with their apps and the apps you can ask for for them."""
    return await my_access.team(session, user)


@router.get("/approvals", response_model=MyApprovals)
async def list_my_approvals(
    session: SessionDep,
    user: CurrentUserDep,
    status_filter: Annotated[
        list[AccessRequestStatus] | None,
        Query(alias="status", description="Repeat for several; pending_manager lists what waits for you"),
    ] = None,
    limit: Limit = 50,
    offset: Offset = 0,
) -> MyApprovals:
    """Requests that wait (or waited) for the signed-in user as the requester's manager, newest first."""
    return await my_approvals.list_mine(session, user, statuses=status_filter, limit=limit, offset=offset)


@router.get("/approvals/{request_id}", response_model=AccessRequestDetail)
async def get_my_approval(request_id: uuid.UUID, session: SessionDep, user: CurrentUserDep) -> AccessRequestDetail:
    """One request with its decisions; 403 unless you are the manager it waits for or the requester's manager."""
    return await my_approvals.detail(session, user, request_id)


@router.post("/approvals/{request_id}/approve", response_model=AccessRequestDetail)
async def approve_my_approval(
    request_id: uuid.UUID,
    data: AccessRequestDecisionCreate,
    session: SessionDep,
    user: CurrentUserDep,
    dispatcher: ActionDispatcherDep,
) -> AccessRequestDetail:
    """Approve as the manager. 403 when you are not, 409 when the manager's step is already decided."""
    return await my_approvals.decide(
        session, user, request_id, outcome=DecisionOutcome.APPROVED, comment=data.comment, dispatcher=dispatcher
    )


@router.post("/approvals/{request_id}/reject", response_model=AccessRequestDetail)
async def reject_my_approval(
    request_id: uuid.UUID,
    data: AccessRequestDecisionCreate,
    session: SessionDep,
    user: CurrentUserDep,
    dispatcher: ActionDispatcherDep,
) -> AccessRequestDetail:
    """Reject as the manager; ``comment`` is required and shown to the person. 403 / 409 as for approve."""
    return await my_approvals.decide(
        session, user, request_id, outcome=DecisionOutcome.REJECTED, comment=data.comment, dispatcher=dispatcher
    )
