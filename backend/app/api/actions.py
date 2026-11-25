import uuid
from typing import Annotated

from fastapi import APIRouter, Query, Response, status

from app.api.deps import ActionDispatcherDep, SessionDep
from app.api.params import DEFAULT_LIMIT, Limit, Offset, SearchQuery
from app.models.enums import ActionStatus
from app.schemas.actions import ActionCreate, ActionList, ActionOut, ActionSecret, BatchApproveResult, NotApproved
from app.services import action_approval, action_queries, action_retry, actions

router = APIRouter(prefix="/actions")


@router.post("", response_model=ActionOut, status_code=status.HTTP_201_CREATED)
async def create_action(data: ActionCreate, session: SessionDep) -> ActionOut:
    """Creates a write waiting for approval (a manual_task when the connector cannot do it).

    A connector write is created even when the connection has writes disabled; approval then fails with 400."""
    action = await actions.create_action(session, data)
    return await action_queries.get_action_out(session, action.id)


@router.get("", response_model=ActionList)
async def list_actions(
    session: SessionDep,
    q: SearchQuery = None,
    status: Annotated[list[ActionStatus] | None, Query(description="Repeat to filter by several statuses")] = None,
    batch_id: uuid.UUID | None = None,
    person_id: uuid.UUID | None = None,
    app_id: uuid.UUID | None = None,
    limit: Limit = DEFAULT_LIMIT,
    offset: Offset = 0,
) -> ActionList:
    """Newest first. ``counts`` has every status, counted with all filters except ``status``."""
    items, total, counts = await action_queries.list_actions(
        session,
        statuses=status,
        batch_id=batch_id,
        person_id=person_id,
        app_id=app_id,
        q=q,
        limit=limit,
        offset=offset,
    )
    return ActionList(items=items, total=total, counts=counts)


@router.post("/batch/{batch_id}/approve", response_model=BatchApproveResult)
async def approve_action_batch(
    batch_id: uuid.UUID, session: SessionDep, dispatcher: ActionDispatcherDep
) -> BatchApproveResult:
    """Approves every pending action of the batch and starts the connector writes.

    Manual tasks wait for a person. Writes whose connection has writes disabled stay pending (``not_approved``)."""
    approved, refused = await action_approval.approve_batch(session, batch_id, dispatcher)
    items = await action_queries.get_actions_out(session, approved)
    refused_out = await action_queries.get_actions_out(session, [action_id for action_id, _ in refused])
    reasons = dict(refused)
    return BatchApproveResult(
        items=items,
        total=len(items),
        not_approved=[NotApproved(action=action, reason=reasons[action.id]) for action in refused_out],
    )


@router.post("/{action_id}/approve", response_model=ActionOut)
async def approve_action(action_id: uuid.UUID, session: SessionDep, dispatcher: ActionDispatcherDep) -> ActionOut:
    """Approves the action. A connector write starts at once (ExecuteActionWorkflow); 400 when the app's
    connection has writes disabled, and the action stays pending."""
    await action_approval.approve(session, action_id, dispatcher)
    return await action_queries.get_action_out(session, action_id)


@router.post("/{action_id}/cancel", response_model=ActionOut)
async def cancel_action(action_id: uuid.UUID, session: SessionDep) -> ActionOut:
    await actions.cancel(session, action_id)
    return await action_queries.get_action_out(session, action_id)


@router.post("/{action_id}/complete", response_model=ActionOut)
async def complete_action(action_id: uuid.UUID, session: SessionDep) -> ActionOut:
    """Closes a manual task as done. A manual create in an app without a connection adds the account."""
    await actions.complete(session, action_id)
    return await action_queries.get_action_out(session, action_id)


@router.post("/{action_id}/retry", response_model=ActionOut)
async def retry_action(action_id: uuid.UUID, session: SessionDep, dispatcher: ActionDispatcherDep) -> ActionOut:
    """Runs a failed connector write again. It reads the app first and writes only when the change is not
    there yet. 400 when writes are disabled, 409 when the action is not a failed write."""
    await action_retry.retry(session, action_id, dispatcher)
    return await action_queries.get_action_out(session, action_id)


@router.post("/{action_id}/by-hand", response_model=ActionOut)
async def do_action_by_hand(action_id: uuid.UUID, session: SessionDep) -> ActionOut:
    """Turns a failed connector write into an approved manual task with the same operation."""
    await action_retry.do_by_hand(session, action_id)
    return await action_queries.get_action_out(session, action_id)


@router.get(
    "/{action_id}/screenshot",
    response_class=Response,
    responses={200: {"content": {"image/png": {}}, "description": "PNG of the tab"}},
)
async def get_action_screenshot(action_id: uuid.UUID, session: SessionDep) -> Response:
    """Where the action's click recipe stopped. 404 when there is none."""
    png = await action_queries.screenshot(session, action_id)
    return Response(content=png, media_type="image/png", headers={"Cache-Control": "no-store"})


@router.post("/{action_id}/reveal-secret", response_model=ActionSecret)
async def reveal_action_secret(action_id: uuid.UUID, session: SessionDep) -> ActionSecret:
    """Returns the one-time secret of the action (temporary password) and deletes it. 404 the second time."""
    return await action_approval.reveal_secret(session, action_id)
