"""``SyncDispatcher`` backed by Temporal (see ``app.services.sync_dispatch``)."""

import uuid

from app.config import settings
from app.temporal.client import get_temporal_client
from app.temporal.schedules import delete_sync_schedule, upsert_sync_schedule
from app.temporal.sync_types import SyncParams
from app.temporal.sync_workflow import SyncConnectionWorkflow


class TemporalSyncDispatcher:
    async def start_sync(self, connection_id: uuid.UUID, sync_run_id: uuid.UUID, *, force: bool) -> None:
        client = await get_temporal_client()
        await client.start_workflow(
            SyncConnectionWorkflow.run,
            SyncParams(connection_id=str(connection_id), sync_run_id=str(sync_run_id), force=force),
            id=f"sync-run-{sync_run_id}",
            task_queue=settings.temporal_task_queue,
        )

    async def upsert_schedule(self, connection_id: uuid.UUID) -> None:
        await upsert_sync_schedule(await get_temporal_client(), connection_id)

    async def delete_schedule(self, connection_id: uuid.UUID) -> None:
        await delete_sync_schedule(await get_temporal_client(), connection_id)


def get_sync_dispatcher() -> TemporalSyncDispatcher:
    """FastAPI dependency; tests override it."""
    return TemporalSyncDispatcher()
