"""``CheckForUpdateWorkflow``: ask GitHub for the newest stable release. Hourly by a Temporal Schedule."""

from datetime import timedelta

from temporalio import workflow
from temporalio.common import RetryPolicy

with workflow.unsafe.imports_passed_through():
    from app.temporal.update_check_activities import check_for_update


@workflow.defn
class CheckForUpdateWorkflow:
    @workflow.run
    async def run(self) -> str:
        # The service never raises for "no answer"; a retry covers only a crash. The next hour tries again.
        return await workflow.execute_activity(
            check_for_update,
            start_to_close_timeout=timedelta(minutes=1),
            retry_policy=RetryPolicy(maximum_attempts=2),
        )
