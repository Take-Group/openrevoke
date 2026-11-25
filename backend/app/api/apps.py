import uuid

from fastapi import APIRouter, Response, status

from app.api.deps import DispatcherDep, SessionDep
from app.api.params import DEFAULT_LIMIT, Limit, Offset, SearchQuery
from app.models.enums import AccountKind, AccountStatus, ConnectionStatus, Integration
from app.schemas.accounts import AccountCreate, AccountOut, AccountPage
from app.schemas.apps import AppCreate, AppDetail, AppPage, AppUpdate
from app.services import accounts, apps
from app.services.sync_dispatch import delete_schedule_quietly

router = APIRouter(prefix="/apps")


@router.get("", response_model=AppPage)
async def list_apps(
    session: SessionDep,
    q: SearchQuery = None,
    status: ConnectionStatus | None = None,
    integration: Integration | None = None,
    limit: Limit = DEFAULT_LIMIT,
    offset: Offset = 0,
) -> AppPage:
    """``status`` filters by connection status."""
    items, total = await apps.list_apps(
        session, q=q, status=status, integration=integration, limit=limit, offset=offset
    )
    return AppPage(items=items, total=total)


@router.post("", response_model=AppDetail, status_code=status.HTTP_201_CREATED)
async def create_app(data: AppCreate, session: SessionDep) -> AppDetail:
    """Adds a SaaS app with its price. Accounts come from a connection (put_connection) or are added by hand."""
    return await apps.create_app(session, data)


@router.get("/{app_id}", response_model=AppDetail)
async def get_app(app_id: uuid.UUID, session: SessionDep) -> AppDetail:
    """One app: price, seats, monthly cost, connection and its last sync."""
    return await apps.get_app(session, app_id)


@router.patch("/{app_id}", response_model=AppDetail)
async def update_app(app_id: uuid.UUID, data: AppUpdate, session: SessionDep) -> AppDetail:
    """Changes an app's name, price or settings. Only the fields present change."""
    return await apps.update_app(session, app_id, data, data.model_fields_set)


@router.delete("/{app_id}", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
async def delete_app(app_id: uuid.UUID, session: SessionDep, dispatcher: DispatcherDep) -> Response:
    """Only an app without accounts and actions. Its connection and sync schedule go with it."""
    connection_id = await apps.delete_app(session, app_id)
    await session.commit()
    if connection_id is not None:
        await delete_schedule_quietly(dispatcher, connection_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{app_id}/accounts", response_model=AccountPage)
async def list_app_accounts(
    app_id: uuid.UUID,
    session: SessionDep,
    q: SearchQuery = None,
    status: AccountStatus | None = None,
    kind: AccountKind | None = None,
    unassigned: bool = False,
    limit: Limit = DEFAULT_LIMIT,
    offset: Offset = 0,
) -> AccountPage:
    """``unassigned=true`` shows accounts without an owner (no person, not a service account, not removed)."""
    items, total = await accounts.list_app_accounts(
        session, app_id, q=q, status=status, kind=kind, unassigned=unassigned, limit=limit, offset=offset
    )
    return AccountPage(items=items, total=total)


@router.post("/{app_id}/accounts", response_model=AccountOut, status_code=status.HTTP_201_CREATED)
async def create_app_account(app_id: uuid.UUID, data: AccountCreate, session: SessionDep) -> AccountOut:
    """Adds an account by hand in an app without a connection (or a seat the connector does not list)."""
    return await accounts.create_manual_account(session, app_id, data)
