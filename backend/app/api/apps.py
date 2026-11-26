import uuid
from typing import Annotated

from fastapi import APIRouter, File, Header, Query, Request, Response, UploadFile, status

from app.api.deps import DispatcherDep, SessionDep
from app.api.params import DEFAULT_LIMIT, Limit, Offset, SearchQuery
from app.models.enums import AccountKind, AccountStatus, ConnectionStatus, Integration
from app.schemas.accounts import AccountCreate, AccountImportResult, AccountOut, AccountPage, AccountsPaste
from app.schemas.apps import AppBulkCreate, AppBulkResult, AppCreate, AppDetail, AppPage, AppUpdate
from app.services import accounts, accounts_import, app_logos, apps, apps_bulk
from app.services.sync_dispatch import delete_schedule_quietly

router = APIRouter(prefix="/apps")
# Any signed-in user (router.py, self_router): My access shows app logos to members too.
logo_router = APIRouter(prefix="/apps")

# A logo is the admin's upload: never sniffed into HTML, and an SVG opened on its own runs no script.
LOGO_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "Content-Security-Policy": "default-src 'none'; style-src 'unsafe-inline'; sandbox",
    "Cache-Control": "private, no-cache",
}

DryRun = Annotated[bool, Query(description="Preview the changes without saving")]


@router.get("", response_model=AppPage)
async def list_apps(
    session: SessionDep,
    q: SearchQuery = None,
    status: ConnectionStatus | None = None,
    integration: Integration | None = None,
    category: Annotated[str | None, Query(max_length=50)] = None,
    limit: Limit = DEFAULT_LIMIT,
    offset: Offset = 0,
) -> AppPage:
    """``status`` filters by connection status; ``categories`` lists every category in use."""
    items, total = await apps.list_apps(
        session, q=q, status=status, integration=integration, category=category, limit=limit, offset=offset
    )
    return AppPage(items=items, total=total, categories=await apps.used_categories(session))


@router.post("", response_model=AppDetail, status_code=status.HTTP_201_CREATED)
async def create_app(data: AppCreate, session: SessionDep) -> AppDetail:
    """Adds a SaaS app with its price. Accounts come from a connection (put_connection) or are added by hand.

    With ``catalog_key`` (from search_catalog) and no ``name``, the name and website come from the catalog.
    """
    return await apps.create_app(session, data)


@router.post("/bulk", response_model=AppBulkResult, status_code=status.HTTP_201_CREATED)
async def create_apps_bulk(data: AppBulkCreate, session: SessionDep) -> AppBulkResult:
    """Adds up to 100 apps (catalog_key or name) as manual and free; apps that exist are skipped with a reason."""
    return await apps_bulk.create_apps(session, data)


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


@router.post("/{app_id}/accounts/bulk", response_model=AccountImportResult)
async def paste_app_accounts(
    app_id: uuid.UUID, data: AccountsPaste, session: SessionDep, dry_run: DryRun = False
) -> AccountImportResult:
    """Adds accounts from pasted e-mails (new lines, commas or semicolons) to a manual app.

    Existing accounts stay as they are. Try ``dry_run=true`` first.
    """
    return await accounts_import.import_emails(session, app_id, data.emails, dry_run=dry_run)


@router.put("/{app_id}/logo", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
async def upload_app_logo(
    app_id: uuid.UUID,
    session: SessionDep,
    file: Annotated[UploadFile, File(description="PNG, JPEG, WebP or SVG, at most 256 KB")],
) -> Response:
    """Sets the app's own logo; it wins over the catalog's. An SVG with scripts or links is refused (400)."""
    content = await file.read(app_logos.MAX_BYTES + 1)
    await app_logos.set_logo(session, app_id, content)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.delete("/{app_id}/logo", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
async def delete_app_logo(app_id: uuid.UUID, session: SessionDep) -> Response:
    """Removes the uploaded logo: the app shows the catalog's logo or its initial again."""
    await app_logos.delete_logo(session, app_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@logo_router.get(
    "/{app_id}/logo",
    response_class=Response,
    responses={200: {"content": {"image/png": {}, "image/svg+xml": {}}}, 304: {"description": "Not modified"}},
)
async def get_app_logo(
    app_id: uuid.UUID,
    session: SessionDep,
    request: Request,
    if_none_match: Annotated[str | None, Header(include_in_schema=False)] = None,
) -> Response:
    """The uploaded logo (``logo_url`` of an app points here). 404 when the app has none."""
    logo = await app_logos.get_logo(session, app_id)
    headers = {**LOGO_HEADERS, "ETag": logo.etag}
    if if_none_match and logo.etag in if_none_match:
        return Response(status_code=status.HTTP_304_NOT_MODIFIED, headers=headers)
    return Response(content=logo.content, media_type=logo.content_type, headers=headers)
