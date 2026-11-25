import asyncio

import structlog
from sqlalchemy import select
from temporalio.worker import Worker

from app.browser.provider import get_browser_provider
from app.config import settings
from app.connectors.browser_api import BrowserUnavailableError
from app.database import async_session
from app.logging import setup_logging
from app.models import Connection
from app.services.discovery_sources import discovery_connection_ids
from app.slack_agent.runner import SlackAgentRunner
from app.temporal.action_activities import ACTION_ACTIVITIES
from app.temporal.action_dispatcher import TemporalActionDispatcher
from app.temporal.action_workflow import ExecuteActionWorkflow
from app.temporal.client import get_temporal_client
from app.temporal.google_setup_activities import GOOGLE_SETUP_ACTIVITIES
from app.temporal.google_setup_workflow import GoogleCloudSetupWorkflow
from app.temporal.rates_activities import RATES_ACTIVITIES
from app.temporal.rates_schedule import ensure_rates
from app.temporal.rates_workflow import RefreshExchangeRatesWorkflow
from app.temporal.scan_activities import SCAN_ACTIVITIES
from app.temporal.scan_schedules import reconcile_scan_schedules
from app.temporal.scan_workflow import ScanConnectionWorkflow
from app.temporal.schedules import reconcile_sync_schedules
from app.temporal.sync_activities import SYNC_ACTIVITIES
from app.temporal.sync_workflow import SyncConnectionWorkflow
from app.temporal.update_check_activities import UPDATE_CHECK_ACTIVITIES
from app.temporal.update_check_schedule import ensure_update_check
from app.temporal.update_check_workflow import CheckForUpdateWorkflow

logger = structlog.get_logger()


async def reconcile_schedules() -> None:
    """One sync schedule per connection and one scan schedule per discovery connection. Never stops the worker."""
    try:
        async with async_session() as session:
            connection_ids = list(await session.scalars(select(Connection.id)))
        upserted, deleted = await reconcile_sync_schedules(await get_temporal_client(), connection_ids)
        logger.info("sync_schedules_reconciled", upserted=upserted, deleted=deleted)
    except Exception as exc:  # noqa: BLE001 - schedules are retried on the next start and on every save
        logger.warning("sync_schedules_reconcile_failed", error=str(exc))
    try:
        async with async_session() as session:
            scan_ids = await discovery_connection_ids(session)
        upserted, deleted = await reconcile_scan_schedules(await get_temporal_client(), scan_ids)
        logger.info("scan_schedules_reconciled", upserted=upserted, deleted=deleted)
    except Exception as exc:  # noqa: BLE001 - retried on the next start and on every "Scan now"
        logger.warning("scan_schedules_reconcile_failed", error=str(exc))


async def connect_browser() -> None:
    """Connect early so header capture sees the panels' traffic before the first browser sync.

    A browser that is down is not an error here: the first browser connector call connects again.
    """
    try:
        await get_browser_provider().connect()
    except BrowserUnavailableError as exc:
        logger.info("browser_not_connected_at_start", error=str(exc))
    except Exception as exc:  # noqa: BLE001 - never let the browser stop the worker
        logger.warning("browser_connect_failed_at_start", error=str(exc))


async def start_worker() -> None:
    client = await get_temporal_client()

    worker = Worker(
        client,
        task_queue=settings.temporal_task_queue,
        workflows=[
            SyncConnectionWorkflow,
            ExecuteActionWorkflow,
            RefreshExchangeRatesWorkflow,
            ScanConnectionWorkflow,
            GoogleCloudSetupWorkflow,
            CheckForUpdateWorkflow,
        ],
        activities=[
            *SYNC_ACTIVITIES,
            *ACTION_ACTIVITIES,
            *RATES_ACTIVITIES,
            *SCAN_ACTIVITIES,
            *GOOGLE_SETUP_ACTIVITIES,
            *UPDATE_CHECK_ACTIVITIES,
        ],
    )
    async with worker:
        logger.info("temporal_worker_started", task_queue=settings.temporal_task_queue)
        await reconcile_schedules()
        await ensure_rates(client)
        await ensure_update_check(client)
        await connect_browser()
        # The Slack agent's Socket Mode connection lives next to the worker: no extra process to run.
        await SlackAgentRunner(TemporalActionDispatcher()).run_forever()


def run() -> None:
    setup_logging(debug=settings.debug)
    asyncio.run(start_worker())
