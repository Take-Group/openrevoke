# Skill: New Temporal Workflow

## What it does
Adds a new Temporal workflow with activities for background/async processing.

## Files involved
One pair of files per workflow. Working examples: `SyncConnectionWorkflow` in
`app/temporal/sync_workflow.py`, `sync_activities.py`, `sync_types.py`
(described in `skills/backend/new-connector.md`), and `ExecuteActionWorkflow`
in `app/temporal/action_workflow.py`, `action_activities.py`,
`action_types.py`, `action_dispatcher.py` (described in
`skills/backend/actions.md`). The action workflow keeps the order of its
steps in a plain function (`app/services/action_flow.py`) that tests run
without Temporal.

- `app/temporal/<name>_workflow.py` — workflow definition
- `app/temporal/<name>_activities.py` — activity definitions (they only call services)
- `app/temporal/<name>_types.py` — dataclass inputs shared by both (safe in the workflow sandbox)
- `app/temporal/worker.py` — register workflow and activities with the worker
- `app/temporal/client.py` — used to start workflows from API endpoints

## Flow
1. **Define activities** in `app/temporal/<name>_activities.py`:
   - Each activity is an `async def` decorated with `@activity.defn`
   - Activities do the actual work (DB calls, HTTP requests, etc.)
2. **Define workflow** in `app/temporal/<name>_workflow.py`:
   - Class decorated with `@workflow.defn`
   - `@workflow.run` method orchestrates the activities
   - Call activities via `workflow.execute_activity()`
3. **Register in worker** — add workflow class and activity functions to `app/temporal/worker.py`
4. **Trigger from API** — through an abstraction (see `SyncDispatcher` in
   `app/services/sync_dispatch.py` and `DispatcherDep` in `app/api/deps.py`),
   so API tests can override it without a Temporal server. Commit the
   database rows the workflow reads before starting it.
5. **Trigger from API (raw client)** — use `temporal_client` from `app/temporal/client.py` to start the workflow

## Example
```python
# app/temporal/email_activities.py
from temporalio import activity

@activity.defn
async def send_email(to: str, subject: str, body: str) -> bool:
    # actual email sending logic
    return True

# app/temporal/email_workflow.py
from datetime import timedelta
from temporalio import workflow

with workflow.unsafe.imports_passed_through():
    from app.temporal.email_activities import send_email

@workflow.defn
class SendEmailWorkflow:
    @workflow.run
    async def run(self, to: str, subject: str, body: str) -> bool:
        return await workflow.execute_activity(
            send_email,
            args=[to, subject, body],
            start_to_close_timeout=timedelta(seconds=30),
        )

# app/temporal/worker.py — add to registrations:
# workflows=[..., SendEmailWorkflow]
# activities=[..., send_email]

# Trigger from endpoint:
from app.temporal.client import get_temporal_client

client = await get_temporal_client()
await client.start_workflow(
    SendEmailWorkflow.run,
    args=["user@example.com", "Hello", "Body"],
    id=f"send-email-{uuid4()}",
    task_queue=settings.temporal_task_queue,
)
```

Ruff: `app/temporal/**` ignores TC001-TC003, because Temporal reads the
annotations of workflows and activities at runtime.

## How to extend
- If a workflow gets complex (many activities) — move it to its own file under `app/temporal/`
- Keep activities small and focused (one responsibility each)
- Use `timedelta` for timeouts — always set explicit timeouts on activities
