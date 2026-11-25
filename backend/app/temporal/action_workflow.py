"""``ExecuteActionWorkflow``: one approved write action.

Started on approval (``app.services.action_approval``) and on a retry
(``app.services.action_retry``, with ``precheck``). Steps and their order
are in ``app.services.action_flow``: start (``running``), precheck on a retry
(``done`` when the app already shows the change), write (``verifying``),
then up to ``verify_attempts`` reads ``verify_delay_seconds`` apart (``done``
or ``failed``). The write is never retried automatically: a second create or
delete could hit the app twice. A crash of any step ends the action as
``failed`` with a hint to check the app by hand.
"""

from datetime import timedelta

from temporalio import workflow
from temporalio.common import RetryPolicy
from temporalio.exceptions import ActivityError

with workflow.unsafe.imports_passed_through():
    from app.services.action_flow import run_action_steps
    from app.temporal.action_activities import (
        fail_action,
        precheck_action,
        start_action,
        verify_action,
        write_action,
    )
    from app.temporal.action_types import ExecuteActionParams, FailActionInput, VerifyActionInput

SHORT = timedelta(seconds=30)
ONCE = RetryPolicy(maximum_attempts=1)
FEW = RetryPolicy(maximum_attempts=3, initial_interval=timedelta(seconds=5))


class _WorkflowSteps:
    def __init__(self, params: ExecuteActionParams) -> None:
        self.params = params
        self.timeout = timedelta(seconds=params.activity_timeout_seconds)

    async def start(self) -> str:
        return await workflow.execute_activity(
            start_action, self.params.action_id, start_to_close_timeout=SHORT, retry_policy=FEW
        )

    async def precheck(self) -> str:
        return await workflow.execute_activity(
            precheck_action, self.params.action_id, start_to_close_timeout=self.timeout, retry_policy=FEW
        )

    async def write(self) -> str:
        return await workflow.execute_activity(
            write_action, self.params.action_id, start_to_close_timeout=self.timeout, retry_policy=ONCE
        )

    async def verify(self, attempt: int, final: bool) -> str:
        return await workflow.execute_activity(
            verify_action,
            VerifyActionInput(action_id=self.params.action_id, attempt=attempt, final=final),
            start_to_close_timeout=self.timeout,
            retry_policy=FEW,
        )

    async def sleep(self, seconds: float) -> None:
        await workflow.sleep(timedelta(seconds=seconds))


@workflow.defn
class ExecuteActionWorkflow:
    @workflow.run
    async def run(self, params: ExecuteActionParams) -> str:
        try:
            return await run_action_steps(
                _WorkflowSteps(params),
                attempts=params.verify_attempts,
                delay_seconds=params.verify_delay_seconds,
                precheck=params.precheck,
            )
        except ActivityError as exc:
            cause = exc.cause or exc
            return await workflow.execute_activity(
                fail_action,
                FailActionInput(
                    action_id=params.action_id,
                    error=f"The action crashed: {cause}. Check the account in the app by hand",
                ),
                start_to_close_timeout=SHORT,
                retry_policy=RetryPolicy(maximum_attempts=5),
            )
