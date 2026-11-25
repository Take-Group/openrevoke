"""``RefreshExchangeRatesWorkflow``: download today's exchange rates. Daily by a Temporal Schedule."""

from datetime import timedelta

from temporalio import workflow
from temporalio.common import RetryPolicy

with workflow.unsafe.imports_passed_through():
    from app.temporal.rates_activities import refresh_exchange_rates


@workflow.defn
class RefreshExchangeRatesWorkflow:
    @workflow.run
    async def run(self) -> str:
        # Sources are public and sometimes slow; retry for about an hour, the next day tries again anyway.
        return await workflow.execute_activity(
            refresh_exchange_rates,
            start_to_close_timeout=timedelta(minutes=2),
            retry_policy=RetryPolicy(initial_interval=timedelta(minutes=1), backoff_coefficient=2, maximum_attempts=6),
        )
