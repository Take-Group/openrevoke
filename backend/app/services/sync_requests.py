"""'Sync now' from the API: create the ``sync_run`` and hand it to the workflow engine."""

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

import structlog
from sqlalchemy import select

from app.models import SyncRun
from app.models.enums import SyncRunStatus
from app.schemas.connections import SyncRunOut
from app.services import audit
from app.services.connection_lock import LOCK_TTL_SECONDS, is_locked
from app.services.connections import get_app_connection
from app.services.errors import ConflictError

if TYPE_CHECKING:
    import uuid

    from sqlalchemy.ext.asyncio import AsyncSession

    from app.services.sync_dispatch import SyncDispatcher

logger = structlog.get_logger()

# A run still "running" after the lock would have expired was lost (worker restart).
STALE_AFTER = timedelta(seconds=LOCK_TTL_SECONDS)


async def request_sync(
    session: AsyncSession, app_id: uuid.UUID, dispatcher: SyncDispatcher, *, force: bool = False
) -> SyncRunOut:
    """Create a running ``sync_run`` and start the workflow. 409 when a sync already runs.

    ``force`` skips the 30% removal threshold for this run (recorded in the audit log).
    """
    _, connection = await get_app_connection(session, app_id)
    if connection is None:
        raise ConflictError("The app has no connection. Save the connection first")
    if await is_locked(connection.id):
        raise ConflictError("A sync or action is already running on this connection")
    now = datetime.now(UTC)
    for running in await session.scalars(
        select(SyncRun).where(SyncRun.connection_id == connection.id, SyncRun.status == SyncRunStatus.RUNNING)
    ):
        if now - running.started_at < STALE_AFTER:
            raise ConflictError("A sync is already running on this connection")
        running.status = SyncRunStatus.FAILED
        running.finished_at = now
        running.error = "Interrupted: no worker finished this sync"

    sync_run = SyncRun(connection_id=connection.id, status=SyncRunStatus.RUNNING, started_at=now)
    session.add(sync_run)
    await session.flush()
    if force:
        await audit.record(session, "sync.forced", "connection", connection.id, {"sync_run_id": str(sync_run.id)})
    # The worker reads the run from the database, so it must be committed before the workflow starts.
    await session.commit()
    try:
        await dispatcher.start_sync(connection.id, sync_run.id, force=force)
    except Exception as exc:  # noqa: BLE001 - shown to the user on the run instead of a 500
        logger.warning("sync_start_failed", connection_id=str(connection.id), error=str(exc))
        sync_run.status = SyncRunStatus.FAILED
        sync_run.finished_at = datetime.now(UTC)
        sync_run.error = f"Could not start the sync workflow: {exc}"
        await session.commit()
    return SyncRunOut.model_validate(sync_run)
