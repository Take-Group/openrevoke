"""Access requests for admins: the list with filters, one request with its decisions, decisions, CSV export."""

import uuid
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Query, Response

from app.api.auth_deps import AdminDep
from app.api.deps import ActionDispatcherDep, SessionDep
from app.api.params import Limit, Offset
from app.models.enums import AccessRequestStatus, DecisionOutcome
from app.schemas.access_requests import (
    AccessRequestDecisionCreate,
    AccessRequestDetail,
    AccessRequestPage,
    WaitingFor,
)
from app.services.access import flow, queries
from app.services.access.decisions import person_id_of_user
from app.services.auth.actor import actor_ref

router = APIRouter(prefix="/access-requests")

StatusFilter = Annotated[
    list[AccessRequestStatus] | None, Query(alias="status", description="Repeat to filter by several statuses")
]
FromFilter = Annotated[datetime | None, Query(alias="from", description="Created at or after")]
ToFilter = Annotated[datetime | None, Query(alias="to", description="Created before")]
WaitingFilter = Annotated[WaitingFor | None, Query(description="Requests waiting for the manager or for an admin")]


def _filter(
    status_filter: list[AccessRequestStatus] | None,
    app_id: uuid.UUID | None,
    person_id: uuid.UUID | None,
    created_from: datetime | None,
    created_to: datetime | None,
    waiting_for: WaitingFor | None,
) -> queries.RequestFilter:
    return queries.RequestFilter(
        statuses=status_filter,
        app_id=app_id,
        person_id=person_id,
        created_from=created_from,
        created_to=created_to,
        waiting_for=waiting_for,
    )


@router.get("", response_model=AccessRequestPage)
async def list_access_requests(
    session: SessionDep,
    status_filter: StatusFilter = None,
    app_id: uuid.UUID | None = None,
    person_id: uuid.UUID | None = None,
    created_from: FromFilter = None,
    created_to: ToFilter = None,
    waiting_for: WaitingFilter = None,
    limit: Limit = 50,
    offset: Offset = 0,
) -> AccessRequestPage:
    """Requests from the panel, the API and Slack, newest first, with who decides next."""
    f = _filter(status_filter, app_id, person_id, created_from, created_to, waiting_for)
    return await queries.list_requests(session, f, limit=limit, offset=offset)


@router.get("/export", response_class=Response, responses={200: {"content": {"text/csv": {}}}})
async def export_access_requests(
    session: SessionDep,
    status_filter: StatusFilter = None,
    app_id: uuid.UUID | None = None,
    person_id: uuid.UUID | None = None,
    created_from: FromFilter = None,
    created_to: ToFilter = None,
    waiting_for: WaitingFilter = None,
) -> Response:
    """CSV of the requests matching the filters, oldest first: person, app, justification, every decision, action."""
    f = _filter(status_filter, app_id, person_id, created_from, created_to, waiting_for)
    body = await queries.export_csv(session, f)
    name = f"access-requests-{datetime.now(UTC):%Y-%m-%d}.csv"
    return Response(
        content=body, media_type="text/csv", headers={"Content-Disposition": f'attachment; filename="{name}"'}
    )


@router.get("/{request_id}", response_model=AccessRequestDetail)
async def get_access_request(request_id: uuid.UUID, session: SessionDep) -> AccessRequestDetail:
    """One request with its decisions (oldest first) and its action."""
    return await queries.detail(session, request_id)


@router.post("/{request_id}/approve", response_model=AccessRequestDetail)
async def approve_access_request(
    request_id: uuid.UUID,
    data: AccessRequestDecisionCreate,
    session: SessionDep,
    admin: AdminDep,
    dispatcher: ActionDispatcherDep,
) -> AccessRequestDetail:
    """The admin step, or the manager's step decided for the manager (recorded as an override).

    400 when writes are off for the app; 403 on your own request; 409 when the request waits for nobody."""
    return await _decide(session, admin.id, request_id, DecisionOutcome.APPROVED, data.comment, dispatcher)


@router.post("/{request_id}/reject", response_model=AccessRequestDetail)
async def reject_access_request(
    request_id: uuid.UUID,
    data: AccessRequestDecisionCreate,
    session: SessionDep,
    admin: AdminDep,
    dispatcher: ActionDispatcherDep,
) -> AccessRequestDetail:
    """Reject with a ``comment`` (required): the person sees it. Cancels the request's pending action."""
    return await _decide(session, admin.id, request_id, DecisionOutcome.REJECTED, data.comment, dispatcher)


async def _decide(
    session: SessionDep,
    user_id: uuid.UUID,
    request_id: uuid.UUID,
    outcome: DecisionOutcome,
    comment: str | None,
    dispatcher: ActionDispatcherDep,
) -> AccessRequestDetail:
    decider = flow.Decider(actor=actor_ref(), person_id=await person_id_of_user(session, user_id), is_admin=True)
    await flow.decide(session, request_id, decider=decider, outcome=outcome, comment=comment, dispatcher=dispatcher)
    await session.commit()
    return await queries.detail(session, request_id)
