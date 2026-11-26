"""App discovery: connect the identity provider, scan, review the apps people sign in to."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Query, status
from sqlalchemy import func, select

from app.api.deps import DispatcherDep, ScanDispatcherDep, SessionDep
from app.api.params import DEFAULT_LIMIT, Limit, Offset, SearchQuery
from app.models import ScanRun
from app.models.enums import DiscoveredAppStatus
from app.schemas.discovery import (
    DiscoveredAppDetail,
    DiscoveredAppPage,
    DiscoveredAppTrack,
    DiscoveredAppUpdate,
    DiscoveryOverview,
    DiscoverySourceCreate,
    PersonDiscoveredAppPage,
    ScanRunOut,
    ScanRunPage,
)
from app.services import discovery, discovery_review
from app.services.discovery_setup import service_account_form, setup_google_source
from app.services.scan_requests import request_scan

router = APIRouter()


@router.get("/discovery", response_model=DiscoveryOverview)
async def get_discovery(session: SessionDep) -> DiscoveryOverview:
    """Source, last scan and counts. ``source`` is null until Google Workspace is connected (onboarding)."""
    return await discovery.overview(session)


@router.post("/discovery/source", response_model=DiscoveryOverview, status_code=status.HTTP_201_CREATED)
async def create_discovery_source(
    data: DiscoverySourceCreate, session: SessionDep, dispatcher: DispatcherDep, scan_dispatcher: ScanDispatcherDep
) -> DiscoveryOverview:
    """Connects Google Workspace (app, connection as people source), then starts a sync and the first scan.

    Checks the directory and the audit log scopes first: 400 with the reason when Google refuses.
    409 when a discovery source already exists.
    """
    config, secrets = service_account_form(data)
    await setup_google_source(session, config, secrets, dispatcher, scan_dispatcher)
    return await discovery.overview(session)


@router.post("/discovery/scan", response_model=ScanRunOut, status_code=status.HTTP_202_ACCEPTED)
async def scan_now(
    session: SessionDep,
    scan_dispatcher: ScanDispatcherDep,
    connection_id: Annotated[uuid.UUID | None, Query(description="Defaults to the first discovery source")] = None,
) -> ScanRunOut:
    """Starts a scan in the background. 409 when one runs. Poll ``GET /api/discovery``."""
    return ScanRunOut.model_validate(await request_scan(session, scan_dispatcher, connection_id))


@router.get("/discovery/scans", response_model=ScanRunPage)
async def list_scans(session: SessionDep, limit: Limit = DEFAULT_LIMIT, offset: Offset = 0) -> ScanRunPage:
    """Discovery scans, newest first, with status and counts."""
    total = await session.scalar(select(func.count()).select_from(ScanRun))
    runs = await session.scalars(select(ScanRun).order_by(ScanRun.started_at.desc()).limit(limit).offset(offset))
    return ScanRunPage(items=[ScanRunOut.model_validate(run) for run in runs], total=total or 0)


@router.get("/discovery/apps", response_model=DiscoveredAppPage)
async def list_discovered_apps(
    session: SessionDep,
    q: SearchQuery = None,
    app_status: Annotated[DiscoveredAppStatus | None, Query(alias="status")] = None,
    at_risk: Annotated[bool, Query(description="Only apps with sign-ins of people who left or were removed")] = False,
    limit: Limit = DEFAULT_LIMIT,
    offset: Offset = 0,
) -> DiscoveredAppPage:
    """Apps with at-risk sign-ins first, then by number of people."""
    items, total = await discovery.list_discovered_apps(
        session, q=q, status=app_status, at_risk=at_risk, limit=limit, offset=offset
    )
    return DiscoveredAppPage(items=items, total=total)


@router.get("/discovery/apps/{discovered_app_id}", response_model=DiscoveredAppDetail)
async def get_discovered_app(discovered_app_id: uuid.UUID, session: SessionDep) -> DiscoveredAppDetail:
    """One discovered app with the people who signed in to it and their risk."""
    return await discovery.get_discovered_app(session, discovered_app_id)


@router.patch("/discovery/apps/{discovered_app_id}", response_model=DiscoveredAppDetail)
async def update_discovered_app(
    discovered_app_id: uuid.UUID, data: DiscoveredAppUpdate, session: SessionDep
) -> DiscoveredAppDetail:
    """Ignore, reset to new, or link an existing app (``app_id``). Only fields present change."""
    await discovery_review.update_discovered_app(session, discovered_app_id, data, data.model_fields_set)
    return await discovery.get_discovered_app(session, discovered_app_id)


@router.post("/discovery/apps/{discovered_app_id}/track", response_model=DiscoveredAppDetail)
async def track_discovered_app(
    discovered_app_id: uuid.UUID, session: SessionDep, data: DiscoveredAppTrack | None = None
) -> DiscoveredAppDetail:
    """Links the app with the same name in Open Revoke, or creates a manual one. Connect it from the app page.

    ``create_accounts`` also adds manual accounts for the people who signed in (active in the directory).
    """
    _, created = await discovery_review.track_discovered_app(session, discovered_app_id, data or DiscoveredAppTrack())
    detail = await discovery.get_discovered_app(session, discovered_app_id)
    detail.accounts_created = created
    return detail


@router.get("/people/{person_id}/discovered-apps", response_model=PersonDiscoveredAppPage)
async def list_person_discovered_apps(person_id: uuid.UUID, session: SessionDep) -> PersonDiscoveredAppPage:
    """Apps the person signed in to with their work account (ignored apps left out)."""
    items = await discovery.person_discovered_apps(session, person_id)
    return PersonDiscoveredAppPage(items=items, total=len(items))
