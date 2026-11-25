"""``GoogleCloudSetupWorkflow``: the automatic Google Cloud setup, one browser run.

No retries: the run creates a project and an OAuth client, and a retry would make them again.
The runner writes failures to the setup state itself.
"""

from datetime import timedelta

from temporalio import workflow
from temporalio.common import RetryPolicy

with workflow.unsafe.imports_passed_through():
    from app.temporal.google_setup_activities import run_google_cloud_setup

# Console steps take a few minutes; the admin has 10 minutes on Google's consent screen.
RUN_TIMEOUT = timedelta(minutes=25)


@workflow.defn
class GoogleCloudSetupWorkflow:
    @workflow.run
    async def run(self) -> None:
        await workflow.execute_activity(
            run_google_cloud_setup,
            start_to_close_timeout=RUN_TIMEOUT,
            heartbeat_timeout=timedelta(minutes=2),
            retry_policy=RetryPolicy(maximum_attempts=1),
        )
