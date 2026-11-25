"""Activities of ``ExecuteActionWorkflow``. They only call ``app.services.action_execution``."""

import uuid

from temporalio import activity

from app.services import action_execution
from app.temporal.action_types import FailActionInput, VerifyActionInput


@activity.defn
async def start_action(action_id: str) -> str:
    return await action_execution.start(uuid.UUID(action_id))


@activity.defn
async def precheck_action(action_id: str) -> str:
    return await action_execution.precheck(uuid.UUID(action_id))


@activity.defn
async def write_action(action_id: str) -> str:
    return await action_execution.write(uuid.UUID(action_id))


@activity.defn
async def verify_action(data: VerifyActionInput) -> str:
    return await action_execution.verify(uuid.UUID(data.action_id), data.attempt, data.final)


@activity.defn
async def fail_action(data: FailActionInput) -> str:
    return await action_execution.fail(uuid.UUID(data.action_id), data.error)


ACTION_ACTIVITIES = [start_action, precheck_action, write_action, verify_action, fail_action]
