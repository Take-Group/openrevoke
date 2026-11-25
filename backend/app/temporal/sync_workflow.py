"""``SyncConnectionWorkflow``: one sync of one connection.

Started by "Sync now" (with the ``sync_run`` the API created) and by the
per-connection Temporal Schedule (``app.temporal.schedules``).
"""

from datetime import timedelta

from temporalio import workflow
from temporalio.common import RetryPolicy
from temporalio.exceptions import ActivityError

with workflow.unsafe.imports_passed_through():
    from app.services.sync import SyncOutcome
    from app.temporal.sync_activities import fail_sync_run, run_sync, start_sync_run
    from app.temporal.sync_types import FailSyncInput, RunSyncInput, SyncParams

SHORT = timedelta(seconds=30)
# The service stops reading after 20 minutes; this leaves time to store the result.
RUN_TIMEOUT = timedelta(minutes=30)


@workflow.defn
class SyncConnectionWorkflow:
    @workflow.run
    async def run(self, params: SyncParams) -> SyncOutcome | None:
        run_id = await workflow.execute_activity(
            start_sync_run, params, start_to_close_timeout=SHORT, retry_policy=RetryPolicy(maximum_attempts=5)
        )
        if run_id is None:
            return None  # connection deleted in the meantime
        try:
            # Connector errors end inside the activity as a failed run; only infrastructure errors retry.
            return await workflow.execute_activity(
                run_sync,
                RunSyncInput(sync_run_id=run_id, force=params.force),
                start_to_close_timeout=RUN_TIMEOUT,
                retry_policy=RetryPolicy(maximum_attempts=3, initial_interval=timedelta(seconds=10)),
            )
        except ActivityError as exc:
            cause = exc.cause or exc
            return await workflow.execute_activity(
                fail_sync_run,
                FailSyncInput(sync_run_id=run_id, error=f"Sync crashed: {cause}"),
                start_to_close_timeout=SHORT,
                retry_policy=RetryPolicy(maximum_attempts=5),
            )
