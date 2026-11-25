"""Temporal Schedule per connection: ``SyncConnectionWorkflow`` every ``SYNC_INTERVAL_HOURS``.

Created or updated when a connection is saved, deleted with the app, and
reconciled with the database when the worker starts.
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
from temporalio.service import RPCError, RPCStatusCode

from app.config import settings
from app.temporal.sync_types import SyncParams
from app.temporal.sync_workflow import SyncConnectionWorkflow

if TYPE_CHECKING:
    from collections.abc import Iterable

    from temporalio.client import Client, ScheduleUpdateInput

SCHEDULE_PREFIX = "sync-connection-"
# Spreads the syncs of many connections instead of starting all at the same second.
JITTER = timedelta(minutes=10)


def schedule_id(connection_id: uuid.UUID) -> str:
    return f"{SCHEDULE_PREFIX}{connection_id}"


def build_schedule(connection_id: uuid.UUID) -> Schedule:
    return Schedule(
        action=ScheduleActionStartWorkflow(
            SyncConnectionWorkflow.run,
            SyncParams(connection_id=str(connection_id)),
            id=f"sync-scheduled-{connection_id}",
            task_queue=settings.temporal_task_queue,
        ),
        spec=ScheduleSpec(
            intervals=[ScheduleIntervalSpec(every=timedelta(hours=settings.sync_interval_hours))], jitter=JITTER
        ),
        policy=SchedulePolicy(overlap=ScheduleOverlapPolicy.SKIP),
    )


async def upsert_sync_schedule(client: Client, connection_id: uuid.UUID) -> None:
    schedule = build_schedule(connection_id)
    try:
        await client.create_schedule(schedule_id(connection_id), schedule)
    except ScheduleAlreadyRunningError:

        def update(_: ScheduleUpdateInput) -> ScheduleUpdate:
            return ScheduleUpdate(schedule=schedule)

        await client.get_schedule_handle(schedule_id(connection_id)).update(update)


async def delete_sync_schedule(client: Client, connection_id: uuid.UUID) -> None:
    try:
        await client.get_schedule_handle(schedule_id(connection_id)).delete()
    except RPCError as exc:
        if exc.status != RPCStatusCode.NOT_FOUND:
            raise


async def reconcile_sync_schedules(client: Client, connection_ids: Iterable[uuid.UUID]) -> tuple[int, int]:
    """Make the schedules match the connections. Returns (upserted, deleted)."""
    wanted = {schedule_id(connection_id): connection_id for connection_id in connection_ids}
    for connection_id in wanted.values():
        await upsert_sync_schedule(client, connection_id)
    deleted = 0
    async for entry in await client.list_schedules():
        if entry.id.startswith(SCHEDULE_PREFIX) and entry.id not in wanted:
            await client.get_schedule_handle(entry.id).delete()
            deleted += 1
    return len(wanted), deleted
