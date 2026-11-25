"""``ScanConnectionWorkflow``: one app discovery scan of one connection.

Started by "Scan now" (with the ``scan_run`` the API created) and by the
per-connection Temporal Schedule (``app.temporal.scan_schedules``).
"""

from datetime import timedelta

from temporalio import workflow
from temporalio.common import RetryPolicy
from temporalio.exceptions import ActivityError

with workflow.unsafe.imports_passed_through():
    from app.services.discovery_scan import ScanOutcome
    from app.temporal.scan_activities import fail_scan_run, run_scan, start_scan_run
    from app.temporal.scan_types import FailScanInput, RunScanInput, ScanParams

SHORT = timedelta(seconds=30)
# The service stops reading after 20 minutes; this leaves time to store the result.
RUN_TIMEOUT = timedelta(minutes=30)


@workflow.defn
class ScanConnectionWorkflow:
    @workflow.run
    async def run(self, params: ScanParams) -> ScanOutcome | None:
        run_id = await workflow.execute_activity(
            start_scan_run, params, start_to_close_timeout=SHORT, retry_policy=RetryPolicy(maximum_attempts=5)
        )
        if run_id is None:
            return None  # connection deleted in the meantime
        try:
            # Connector errors end inside the activity as a failed run; only infrastructure errors retry.
            return await workflow.execute_activity(
                run_scan,
                RunScanInput(scan_run_id=run_id),
                start_to_close_timeout=RUN_TIMEOUT,
                retry_policy=RetryPolicy(maximum_attempts=3, initial_interval=timedelta(seconds=10)),
            )
        except ActivityError as exc:
            cause = exc.cause or exc
            return await workflow.execute_activity(
                fail_scan_run,
                FailScanInput(scan_run_id=run_id, error=f"Scan crashed: {cause}"),
                start_to_close_timeout=SHORT,
                retry_policy=RetryPolicy(maximum_attempts=5),
            )
