"""One app discovery scan of a connection. Called by the activities of ``ScanConnectionWorkflow``.

Steps, like the account sync (``app.services.sync``):

1. ``start_run``: the ``scan_run`` row (the API creates it for "Scan now",
   a scheduled run creates it here).
2. ``run``: under the scan lock of the connection, read with no transaction
   open, then store everything in one transaction. A connector error ends
   the run as ``failed`` and changes nothing else. The scan never changes
   the connection status: that belongs to the account sync.
3. ``fail_run``: the workflow's last resort when ``run`` crashed for good.

The scan has its own lock, not the connection lock: a scan reads for
minutes, and a sync that finds the connection lock taken gives up.
"""

import asyncio
from contextlib import asynccontextmanager, suppress
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

import httpx
import structlog
from redis.exceptions import LockError
from sqlalchemy import select

from app.config import settings
from app.connectors.base import Capability
from app.connectors.discovery import AppDiscovery
from app.connectors.errors import ConnectorError
from app.connectors.http import build_http_client
from app.database import async_session
from app.models import Connection, ScanRun
from app.models.enums import ScanRunStatus
from app.redis import redis_client
from app.services import audit
from app.services.connector_runtime import HttpFactory, open_context
from app.services.discovery_apply import apply_discovery
from app.services.secret_box import SecretsUnreadableError

if TYPE_CHECKING:
    import uuid
    from collections.abc import AsyncIterator

    from app.connectors.discovery import DiscoveryResult

logger = structlog.get_logger()

FETCH_TIMEOUT_SECONDS = 20 * 60
SCAN_LOCK_TTL_SECONDS = 60 * 60
# Reports API refuses an end time after the request time; a small margin covers clock skew.
END_MARGIN = timedelta(minutes=2)
CONNECTOR_ERRORS = (ConnectorError, SecretsUnreadableError, httpx.HTTPError, TimeoutError)


class ScanBusyError(Exception):
    def __init__(self) -> None:
        super().__init__("Another scan is running on this connection")


def scan_lock_key(connection_id: uuid.UUID) -> str:
    return f"open-revoke:scan-lock:{connection_id}"


async def is_scan_locked(connection_id: uuid.UUID) -> bool:
    return bool(await redis_client.exists(scan_lock_key(connection_id)))


@asynccontextmanager
async def scan_lock(connection_id: uuid.UUID) -> AsyncIterator[None]:
    lock = redis_client.lock(scan_lock_key(connection_id), timeout=SCAN_LOCK_TTL_SECONDS, blocking=False)
    if not await lock.acquire():
        raise ScanBusyError
    try:
        yield
    finally:
        with suppress(LockError):
            await lock.release()


@dataclass
class ScanOutcome:
    scan_run_id: str | None
    status: str
    apps_found: int = 0
    apps_new: int = 0
    grants_found: int = 0
    error: str | None = None


async def start_run(connection_id: uuid.UUID, scan_run_id: uuid.UUID | None) -> uuid.UUID | None:
    """Return the run to execute: the given one, or a new one for a scheduled scan. ``None`` when gone."""
    async with async_session() as session:
        if scan_run_id is not None:
            run = await session.get(ScanRun, scan_run_id)
            return run.id if run is not None else None
        if await session.get(Connection, connection_id) is None:
            return None
        run = ScanRun(connection_id=connection_id, status=ScanRunStatus.RUNNING)
        session.add(run)
        await session.commit()
        return run.id


async def scan_window(connection_id: uuid.UUID, now: datetime) -> tuple[datetime, datetime]:
    """From the end of the last successful scan minus the overlap, or the full lookback for the first one."""
    until = now - END_MARGIN
    earliest = until - timedelta(days=settings.scan_lookback_days)
    async with async_session() as session:
        last_until = await session.scalar(
            select(ScanRun.events_until)
            .where(ScanRun.connection_id == connection_id, ScanRun.status == ScanRunStatus.OK)
            .order_by(ScanRun.events_until.desc().nulls_last())
            .limit(1)
        )
    if last_until is None:
        return earliest, until
    return max(earliest, last_until - timedelta(hours=settings.scan_overlap_hours)), until


async def run(scan_run_id: uuid.UUID, *, http_factory: HttpFactory = build_http_client) -> ScanOutcome:
    async with async_session() as session:
        scan_run = await session.get(ScanRun, scan_run_id)
        if scan_run is None:
            return ScanOutcome(scan_run_id=None, status="skipped", error="Scan run not found")
        if scan_run.status != ScanRunStatus.RUNNING:
            return _outcome(scan_run)  # a retried activity: the run already finished
        connection_id = scan_run.connection_id
    try:
        async with scan_lock(connection_id):
            return await _run_locked(scan_run_id, connection_id, http_factory)
    except ScanBusyError as exc:
        return await fail_run(scan_run_id, str(exc))


async def fail_run(scan_run_id: uuid.UUID, error: str) -> ScanOutcome:
    async with async_session() as session:
        scan_run = await session.get(ScanRun, scan_run_id)
        if scan_run is None:
            return ScanOutcome(scan_run_id=None, status="skipped", error=error)
        scan_run.status = ScanRunStatus.FAILED
        scan_run.finished_at = datetime.now(UTC)
        scan_run.error = error
        await session.commit()
        outcome = _outcome(scan_run)
    logger.warning("scan_failed", scan_run_id=str(scan_run_id), error=error)
    return outcome


async def _run_locked(scan_run_id: uuid.UUID, connection_id: uuid.UUID, http_factory: HttpFactory) -> ScanOutcome:
    async with async_session() as session:
        connection = await session.get(Connection, connection_id)
    if connection is None:
        return ScanOutcome(scan_run_id=str(scan_run_id), status="skipped", error="Connection deleted")
    since, until = await scan_window(connection_id, datetime.now(UTC))
    try:
        async with asyncio.timeout(FETCH_TIMEOUT_SECONDS):
            result = await _fetch(connection, since, until, http_factory)
    except CONNECTOR_ERRORS as exc:
        message = str(exc) or exc.__class__.__name__
        if isinstance(exc, TimeoutError):
            message = f"The scan did not finish reading within {FETCH_TIMEOUT_SECONDS // 60} minutes"
        elif isinstance(exc, httpx.HTTPError):
            message = f"Network error while scanning: {exc.__class__.__name__}: {exc}"
        return await fail_run(scan_run_id, message)

    async with async_session() as session:
        connection = await session.get(Connection, connection_id)
        scan_run = await session.get(ScanRun, scan_run_id)
        if connection is None or scan_run is None:
            return ScanOutcome(scan_run_id=str(scan_run_id), status="skipped", error="Connection deleted")
        stats = await apply_discovery(session, connection, result)
        scan_run.status = ScanRunStatus.OK
        scan_run.finished_at = datetime.now(UTC)
        scan_run.events_from = result.events_from
        scan_run.events_until = result.events_until
        scan_run.users_scanned = len(result.directory)
        scan_run.apps_found = stats.apps_found
        scan_run.apps_new = stats.apps_new
        scan_run.grants_found = stats.grants_found
        scan_run.token_inventory = result.token_inventory
        scan_run.notes = result.notes or None
        scan_run.error = None
        await audit.record(
            session,
            "discovery.scan_finished",
            "scan_run",
            scan_run.id,
            {
                "app_id": str(connection.app_id),
                "apps_found": stats.apps_found,
                "apps_new": stats.apps_new,
                "new_apps": stats.new_app_names[:50],
                "grants_found": stats.grants_found,
            },
        )
        await session.commit()
        outcome = _outcome(scan_run)
    logger.info("scan_finished", connection_id=str(connection_id), apps=outcome.apps_found, new=outcome.apps_new)
    return outcome


async def _fetch(
    connection: Connection, since: datetime, until: datetime, http_factory: HttpFactory
) -> DiscoveryResult:
    async with open_context(connection, http_factory) as (connector, ctx):
        if not connector.supports(Capability.DISCOVER_APPS) or not isinstance(connector, AppDiscovery):
            raise ConnectorError(f"{connector.display_name} cannot scan for apps")
        return await connector.discover_apps(ctx, since, until)


def _outcome(scan_run: ScanRun) -> ScanOutcome:
    return ScanOutcome(
        scan_run_id=str(scan_run.id),
        status=str(scan_run.status),
        apps_found=scan_run.apps_found,
        apps_new=scan_run.apps_new,
        grants_found=scan_run.grants_found,
        error=scan_run.error,
    )
