"""``ScanDispatcher`` backed by Temporal (see ``app.services.scan_dispatch``)."""

import uuid

from app.config import settings
from app.temporal.client import get_temporal_client
from app.temporal.scan_schedules import upsert_scan_schedule
from app.temporal.scan_types import ScanParams
from app.temporal.scan_workflow import ScanConnectionWorkflow


class TemporalScanDispatcher:
    async def start_scan(self, connection_id: uuid.UUID, scan_run_id: uuid.UUID) -> None:
        client = await get_temporal_client()
        await client.start_workflow(
            ScanConnectionWorkflow.run,
            ScanParams(connection_id=str(connection_id), scan_run_id=str(scan_run_id)),
            id=f"scan-run-{scan_run_id}",
            task_queue=settings.temporal_task_queue,
        )

    async def upsert_scan_schedule(self, connection_id: uuid.UUID) -> None:
        await upsert_scan_schedule(await get_temporal_client(), connection_id)


def get_scan_dispatcher() -> TemporalScanDispatcher:
    """FastAPI dependency; tests override it."""
    return TemporalScanDispatcher()
