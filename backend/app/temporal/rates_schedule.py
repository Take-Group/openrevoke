"""Daily Temporal Schedule for exchange rates, and a download at worker start when today's rates are missing."""

from datetime import UTC, datetime

import structlog
from temporalio.client import (
    Client,
    Schedule,
    ScheduleActionStartWorkflow,
    ScheduleAlreadyRunningError,
    ScheduleOverlapPolicy,
    SchedulePolicy,
    ScheduleSpec,
    ScheduleUpdate,
    ScheduleUpdateInput,
)
from temporalio.common import WorkflowIDConflictPolicy
from temporalio.exceptions import WorkflowAlreadyStartedError

from app.config import settings
from app.database import async_session
from app.services import exchange_rates
from app.temporal.rates_workflow import RefreshExchangeRatesWorkflow

logger = structlog.get_logger()

SCHEDULE_ID = "exchange-rates-daily"
# ExchangeRate-API publishes the new day shortly after 00:00 UTC.
CRON = "30 2 * * *"


def build_schedule() -> Schedule:
    return Schedule(
        action=ScheduleActionStartWorkflow(
            RefreshExchangeRatesWorkflow.run, id="exchange-rates-scheduled", task_queue=settings.temporal_task_queue
        ),
        spec=ScheduleSpec(cron_expressions=[CRON]),
        policy=SchedulePolicy(overlap=ScheduleOverlapPolicy.SKIP),
    )


async def upsert_rates_schedule(client: Client) -> None:
    schedule = build_schedule()
    try:
        await client.create_schedule(SCHEDULE_ID, schedule)
    except ScheduleAlreadyRunningError:

        def update(_: ScheduleUpdateInput) -> ScheduleUpdate:
            return ScheduleUpdate(schedule=schedule)

        await client.get_schedule_handle(SCHEDULE_ID).update(update)


async def ensure_rates(client: Client) -> None:
    """Schedule the daily download; start one now when there are no rates for today. Never raises."""
    try:
        await upsert_rates_schedule(client)
        today = datetime.now(UTC).date()
        async with async_session() as session:
            fresh = await exchange_rates.has_rates_for(session, today)
        if not fresh:
            await client.start_workflow(
                RefreshExchangeRatesWorkflow.run,
                id=f"exchange-rates-{today.isoformat()}",
                task_queue=settings.temporal_task_queue,
                id_conflict_policy=WorkflowIDConflictPolicy.USE_EXISTING,
            )
        logger.info("exchange_rates_schedule_ready", started_now=not fresh)
    except WorkflowAlreadyStartedError:
        pass  # today's refresh is already running: nothing to start
    except Exception as exc:  # noqa: BLE001 - rates are retried by the schedule; never stop the worker
        logger.warning("exchange_rates_schedule_failed", error=str(exc))
