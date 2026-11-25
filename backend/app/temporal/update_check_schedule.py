"""Hourly Temporal Schedule for the update check, and one check at worker start.

Jitter spreads installations over the hour so they do not all ask GitHub at :00.
With the check off (``OPEN_REVOKE_UPDATE_CHECK=false`` or a ``dev`` build) the schedule is removed.
"""

from datetime import timedelta

import structlog
from temporalio.client import (
    Client,
    Schedule,
    ScheduleActionStartWorkflow,
    ScheduleAlreadyRunningError,
    ScheduleIntervalSpec,
    ScheduleOverlapPolicy,
    SchedulePolicy,
    ScheduleSpec,
    ScheduleUpdate,
    ScheduleUpdateInput,
)
from temporalio.common import WorkflowIDConflictPolicy
from temporalio.service import RPCError, RPCStatusCode

from app.config import settings
from app.services import update_check
from app.temporal.update_check_workflow import CheckForUpdateWorkflow

logger = structlog.get_logger()

SCHEDULE_ID = "update-check-hourly"
JITTER = timedelta(minutes=30)


def build_schedule() -> Schedule:
    return Schedule(
        action=ScheduleActionStartWorkflow(
            CheckForUpdateWorkflow.run, id="update-check-scheduled", task_queue=settings.temporal_task_queue
        ),
        spec=ScheduleSpec(intervals=[ScheduleIntervalSpec(every=timedelta(hours=1))], jitter=JITTER),
        policy=SchedulePolicy(overlap=ScheduleOverlapPolicy.SKIP),
    )


async def _upsert(client: Client) -> None:
    schedule = build_schedule()
    try:
        await client.create_schedule(SCHEDULE_ID, schedule)
    except ScheduleAlreadyRunningError:

        def update(_: ScheduleUpdateInput) -> ScheduleUpdate:
            return ScheduleUpdate(schedule=schedule)

        await client.get_schedule_handle(SCHEDULE_ID).update(update)


async def _delete(client: Client) -> None:
    try:
        await client.get_schedule_handle(SCHEDULE_ID).delete()
    except RPCError as exc:
        if exc.status != RPCStatusCode.NOT_FOUND:
            raise


async def ensure_update_check(client: Client) -> None:
    """Keep the schedule in line with the setting and check once now. Never raises."""
    try:
        if not update_check.enabled():
            await _delete(client)
            logger.info("update_check_off", version=settings.version)
            return
        await _upsert(client)
        await client.start_workflow(
            CheckForUpdateWorkflow.run,
            id="update-check-at-start",
            task_queue=settings.temporal_task_queue,
            id_conflict_policy=WorkflowIDConflictPolicy.USE_EXISTING,
        )
        logger.info("update_check_schedule_ready")
    except Exception as exc:  # noqa: BLE001 - an update notice must never stop the worker
        logger.warning("update_check_schedule_failed", error=str(exc))
