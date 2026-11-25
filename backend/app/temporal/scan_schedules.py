"""Temporal Schedule per discovery connection: ``ScanConnectionWorkflow`` every ``SCAN_INTERVAL_HOURS``.

Created on setup and on "Scan now", reconciled with the database when the worker starts.
"""

import uuid
from datetime import timedelta
from typing import TYPE_CHECKING

from temporalio.client import (
    Schedule,
    ScheduleActionStartWorkflow,
    ScheduleAlreadyRunningError,
    ScheduleIntervalSpec,
    ScheduleOverlapPolicy,
    SchedulePolicy,
    ScheduleSpec,
    ScheduleUpdate,
)

from app.config import settings
from app.temporal.scan_types import ScanParams
from app.temporal.scan_workflow import ScanConnectionWorkflow

if TYPE_CHECKING:
    from collections.abc import Iterable

    from temporalio.client import Client, ScheduleUpdateInput

SCHEDULE_PREFIX = "scan-connection-"
JITTER = timedelta(minutes=30)


def schedule_id(connection_id: uuid.UUID) -> str:
    return f"{SCHEDULE_PREFIX}{connection_id}"


def build_schedule(connection_id: uuid.UUID) -> Schedule:
    return Schedule(
        action=ScheduleActionStartWorkflow(
            ScanConnectionWorkflow.run,
            ScanParams(connection_id=str(connection_id)),
            id=f"scan-scheduled-{connection_id}",
            task_queue=settings.temporal_task_queue,
        ),
        spec=ScheduleSpec(
            intervals=[ScheduleIntervalSpec(every=timedelta(hours=settings.scan_interval_hours))], jitter=JITTER
        ),
        policy=SchedulePolicy(overlap=ScheduleOverlapPolicy.SKIP),
    )


async def upsert_scan_schedule(client: Client, connection_id: uuid.UUID) -> None:
    schedule = build_schedule(connection_id)
    try:
        await client.create_schedule(schedule_id(connection_id), schedule)
    except ScheduleAlreadyRunningError:

        def update(_: ScheduleUpdateInput) -> ScheduleUpdate:
            return ScheduleUpdate(schedule=schedule)

        await client.get_schedule_handle(schedule_id(connection_id)).update(update)


async def reconcile_scan_schedules(client: Client, connection_ids: Iterable[uuid.UUID]) -> tuple[int, int]:
    """Make the schedules match the discovery connections. Returns (upserted, deleted)."""
    wanted = {schedule_id(connection_id): connection_id for connection_id in connection_ids}
    for connection_id in wanted.values():
        await upsert_scan_schedule(client, connection_id)
    deleted = 0
    async for entry in await client.list_schedules():
        if entry.id.startswith(SCHEDULE_PREFIX) and entry.id not in wanted:
            await client.get_schedule_handle(entry.id).delete()
            deleted += 1
    return len(wanted), deleted
