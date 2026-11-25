"""Connectors, connections and syncs."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Query, status
from sqlalchemy import func, select

from app.api.deps import DispatcherDep, SessionDep
from app.api.params import DEFAULT_LIMIT, Limit, Offset
from app.models import App, Connection, SyncRun
from app.schemas.connections import (
    ConnectionCheckResult,
    ConnectionOut,
    ConnectionUpsert,
    ConnectorPage,
    SyncRunOut,
    SyncRunPage,
)
from app.services import connections
from app.services.apps import connection_out
from app.services.errors import NotFoundError
from app.services.sync_dispatch import upsert_schedule_quietly
from app.services.sync_requests import request_sync

router = APIRouter()


@router.get("/connectors", response_model=ConnectorPage, tags=["connections"])
async def list_connectors() -> ConnectorPage:
    """Catalog of connectors with the JSON schema of each connection form. Secret fields are marked."""
    items = connections.catalog()
    return ConnectorPage(items=items, total=len(items))


@router.put("/apps/{app_id}/connection", response_model=ConnectionOut)
async def put_connection(
    app_id: uuid.UUID, data: ConnectionUpsert, session: SessionDep, dispatcher: DispatcherDep
) -> ConnectionOut:
    """Create or update the app's connection and its sync schedule. Secrets are never returned."""
    connection = await connections.upsert_connection(session, app_id, data)
    await session.commit()
    await upsert_schedule_quietly(dispatcher, connection.id)
    return connection_out(connection)


@router.post("/apps/{app_id}/connection/check", response_model=ConnectionCheckResult)
async def check_connection(app_id: uuid.UUID, session: SessionDep) -> ConnectionCheckResult:
    """Calls the app once with the stored settings. ``ok=false`` comes with a message, not an HTTP error."""
    return await connections.check_connection(session, app_id)


@router.post("/apps/{app_id}/connection/sync", response_model=SyncRunOut, status_code=status.HTTP_202_ACCEPTED)
async def sync_connection(
    app_id: uuid.UUID,
    session: SessionDep,
    dispatcher: DispatcherDep,
    force: Annotated[
        bool, Query(description="Skip the 30% removal threshold for this run. Use after checking the removals")
    ] = False,
) -> SyncRunOut:
    """Starts a sync in the background and returns the new sync run (status ``running``).

    409 when a sync or action already runs on the connection. Poll ``GET /api/apps/{app_id}/sync-runs``.
    """
    return await request_sync(session, app_id, dispatcher, force=force)


@router.get("/apps/{app_id}/sync-runs", response_model=SyncRunPage)
async def list_sync_runs(
    app_id: uuid.UUID, session: SessionDep, limit: Limit = DEFAULT_LIMIT, offset: Offset = 0
) -> SyncRunPage:
    """Account syncs of the app's connection, newest first: status, counts, error."""
    if await session.get(App, app_id) is None:
        raise NotFoundError("App not found")
    query = select(SyncRun).join(Connection, Connection.id == SyncRun.connection_id).where(Connection.app_id == app_id)
    total = await session.scalar(select(func.count()).select_from(query.subquery()))
    runs = await session.scalars(query.order_by(SyncRun.started_at.desc()).limit(limit).offset(offset))
    return SyncRunPage(items=[SyncRunOut.model_validate(run) for run in runs], total=total or 0)
