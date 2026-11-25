"""``ActionDispatcher`` backed by Temporal (see ``app.services.action_dispatch``)."""

import uuid

from app.config import settings
from app.services.action_execution import WRITE_TIMEOUT_SECONDS
from app.services.sync import FETCH_TIMEOUT_SECONDS
from app.temporal.action_types import ExecuteActionParams
from app.temporal.action_workflow import ExecuteActionWorkflow
from app.temporal.client import get_temporal_client

# Room to store the result after the connector's own limit.
MARGIN_SECONDS = 5 * 60


class TemporalActionDispatcher:
    async def start_action(self, action_id: uuid.UUID, *, retry: int = 0) -> None:
        client = await get_temporal_client()
        connector_limit = max(WRITE_TIMEOUT_SECONDS, FETCH_TIMEOUT_SECONDS)
        await client.start_workflow(
            ExecuteActionWorkflow.run,
            ExecuteActionParams(
                action_id=str(action_id),
                verify_attempts=settings.action_verify_attempts,
                verify_delay_seconds=settings.action_verify_delay_seconds,
                activity_timeout_seconds=settings.action_lock_wait_seconds + connector_limit + MARGIN_SECONDS,
                precheck=retry > 0,
            ),
            id=f"action-{action_id}" if retry == 0 else f"action-{action_id}-retry-{retry}",
            task_queue=settings.temporal_task_queue,
        )


def get_action_dispatcher() -> TemporalActionDispatcher:
    """FastAPI dependency; tests override it."""
    return TemporalActionDispatcher()
