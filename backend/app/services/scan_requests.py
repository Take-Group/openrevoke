"""'Scan now' from the API: create the ``scan_run`` and hand it to the workflow engine."""

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

import structlog
from sqlalchemy import select

from app.models import Connection, ScanRun
from app.models.enums import ScanRunStatus
from app.services.discovery_scan import SCAN_LOCK_TTL_SECONDS, is_scan_locked
from app.services.discovery_sources import discovery_connections, discovery_keys
from app.services.errors import ConflictError, InvalidInputError, NotFoundError
from app.services.scan_dispatch import upsert_scan_schedule_quietly

if TYPE_CHECKING:
    import uuid

    from sqlalchemy.ext.asyncio import AsyncSession

    from app.services.scan_dispatch import ScanDispatcher

logger = structlog.get_logger()

STALE_AFTER = timedelta(seconds=SCAN_LOCK_TTL_SECONDS)


async def resolve_source(session: AsyncSession, connection_id: uuid.UUID | None) -> Connection:
    if connection_id is None:
        connections = await discovery_connections(session)
        if not connections:
            raise ConflictError("Connect Google Workspace first: no connection can scan for apps")
        return connections[0]
    connection = await session.get(Connection, connection_id)
    if connection is None:
        raise NotFoundError("Connection not found")
    if connection.connector_key not in discovery_keys():
        raise InvalidInputError("This connection cannot scan for apps")
    return connection


async def request_scan(
    session: AsyncSession, dispatcher: ScanDispatcher, connection_id: uuid.UUID | None = None
) -> ScanRun:
    """Create a running ``scan_run`` and start the workflow. 409 when a scan already runs."""
    connection = await resolve_source(session, connection_id)
    if await is_scan_locked(connection.id):
        raise ConflictError("A scan is already running")
    now = datetime.now(UTC)
    for running in await session.scalars(
        select(ScanRun).where(ScanRun.connection_id == connection.id, ScanRun.status == ScanRunStatus.RUNNING)
    ):
        if now - running.started_at < STALE_AFTER:
            raise ConflictError("A scan is already running")
        running.status = ScanRunStatus.FAILED
        running.finished_at = now
        running.error = "Interrupted: no worker finished this scan"

    scan_run = ScanRun(connection_id=connection.id, status=ScanRunStatus.RUNNING, started_at=now)
    session.add(scan_run)
    # The worker reads the run from the database, so it must be committed before the workflow starts.
    await session.commit()
    try:
        await dispatcher.start_scan(connection.id, scan_run.id)
    except Exception as exc:  # noqa: BLE001 - shown to the user on the run instead of a 500
        logger.warning("scan_start_failed", connection_id=str(connection.id), error=str(exc))
        scan_run.status = ScanRunStatus.FAILED
        scan_run.finished_at = datetime.now(UTC)
        scan_run.error = f"Could not start the scan workflow: {exc}"
        await session.commit()
        return scan_run
    await upsert_scan_schedule_quietly(dispatcher, connection.id)
    return scan_run
