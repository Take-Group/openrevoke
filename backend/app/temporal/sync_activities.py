"""Activities of ``SyncConnectionWorkflow``. They only call ``app.services.sync``."""

import uuid

from temporalio import activity

from app.services import sync
from app.services.sync import SyncOutcome
from app.temporal.sync_types import FailSyncInput, RunSyncInput, SyncParams


@activity.defn
async def start_sync_run(params: SyncParams) -> str | None:
    run_id = await sync.start_run(
        uuid.UUID(params.connection_id), uuid.UUID(params.sync_run_id) if params.sync_run_id else None
    )
    return str(run_id) if run_id else None


@activity.defn
async def run_sync(data: RunSyncInput) -> SyncOutcome:
    return await sync.run(uuid.UUID(data.sync_run_id), force=data.force)


@activity.defn
async def fail_sync_run(data: FailSyncInput) -> SyncOutcome:
    return await sync.fail_run(uuid.UUID(data.sync_run_id), data.error)


SYNC_ACTIVITIES = [start_sync_run, run_sync, fail_sync_run]
