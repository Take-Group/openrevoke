"""Order of the steps of one write action, shared by ``ExecuteActionWorkflow`` and tests.

Pure orchestration without I/O: the workflow passes steps that run Temporal
activities and ``workflow.sleep``; tests pass steps that call
``app.services.action_execution`` directly. Statuses are plain strings so the
module is safe in the workflow sandbox.
"""

from typing import Protocol

RUNNING = "running"
VERIFYING = "verifying"
RETRY = "retry"


class ActionSteps(Protocol):
    async def start(self) -> str: ...

    async def precheck(self) -> str: ...

    async def write(self) -> str: ...

    async def verify(self, attempt: int, final: bool) -> str: ...

    async def sleep(self, seconds: float) -> None: ...


async def run_action_steps(steps: ActionSteps, *, attempts: int, delay_seconds: float, precheck: bool = False) -> str:
    """start, (precheck), write, then up to ``attempts`` verification reads ``delay_seconds`` apart.

    ``precheck`` (a retry) reads before the write and ends ``done`` when the change is already there.
    Returns the final status.
    """
    status = await steps.start()
    if status != RUNNING:
        return status
    if precheck:
        status = await steps.precheck()
        if status != RUNNING:
            return status
    status = await steps.write()
    if status != VERIFYING:
        return status
    for attempt in range(1, attempts + 1):
        status = await steps.verify(attempt, attempt == attempts)
        if status != RETRY:
            return status
        await steps.sleep(delay_seconds)
    return status
