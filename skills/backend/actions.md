# Skill: write actions, ExecuteActionWorkflow, verification, secrets

## What it does

An action is a write to an app (`create_account`, `delete_account`) or
a manual task (`manual_task`). Nothing happens without approval by
a person. `ExecuteActionWorkflow` runs an approved connector write,
and a fresh `list_accounts` read confirms the result.

## Files

| File | What it does |
|---|---|
| `backend/app/services/capabilities.py` | `connector_supports`, `write_mode` (`automatic`, `writes_disabled`, `manual`), `delete_suspends` |
| `backend/app/services/actions.py` | `TRANSITIONS`, `create_action`, `advance` (transition with audit), `cancel`, `complete`, closing a manual task |
| `backend/app/services/action_approval.py` | `approve`, `approve_batch`, `start_workflow`, `ensure_can_run` (400 without `writes_enabled`), `reveal_secret` |
| `backend/app/services/action_retry.py` | `retry` (retry of a failed write with a read before the write), `do_by_hand` (change into a manual task) |
| `backend/app/services/action_execution.py` | workflow steps: `start`, `precheck`, `write`, `verify`, `fail` (recipe screenshot in `action_screenshot`) |
| `backend/app/services/action_flow.py` | order of steps (`run_action_steps`), `ActionSteps` protocol |
| `backend/app/services/action_accounts.py` | accounts after an action: `apply_created`, `apply_deleted`, `add_manual_account` |
| `backend/app/services/action_queries.py` | list with `counts` per status, `get_action_out`, `ActionOut` |
| `backend/app/services/action_dispatch.py` | `ActionDispatcher` interface (workflow start) |
| `backend/app/temporal/action_workflow.py`, `action_activities.py`, `action_types.py`, `action_dispatcher.py` | workflow, activities, inputs, start from the API |
| `backend/app/api/actions.py` | `POST /api/actions`, `GET /api/actions`, `/approve`, `/cancel`, `/complete`, `/retry`, `/by-hand`, `/reveal-secret`, `GET /screenshot`, `/batch/{id}/approve` |
| `backend/app/connectors/fake/state.py`, `browser_fake/panel_state.py` | writes of the test connectors in Redis |

## Lifecycle

```
pending_approval ──approve──> approved ──start──> running ──write──> verifying ──verify──> done
        │                         │                  │                    └──(last read without confirmation)──> failed
        └──cancel──> cancelled    └──(manual_task)── complete ──> done

failed ──retry──> approved (new run: start, precheck, write, verify)
failed ──by-hand──> approved as manual_task ── complete ──> done
```

1. **Creation** (`create_action`). The kind follows from the connector of the app's
   connection: if it has `Capability.CREATE_ACCOUNT` / `DELETE_ACCOUNT`, it is a write,
   otherwise a `manual_task` with `payload.operation`. `writes_enabled` does not matter
   here: the action is created also when writes are disabled.
2. **Approval** (`action_approval.approve`). A connector write needs
   `writes_enabled`, otherwise 400 "Writes are disabled for …" and the action stays
   `pending_approval`. After approval the service commits and calls
   `ActionDispatcher.start_action`. A Temporal start error gives `failed`
   with a description. A `manual_task` waits for a person after approval.
3. **Batch** (`approve_batch`). It approves what it can. Writes with writes
   disabled stay `pending_approval` and come back in `not_approved` with a reason.
   Each write is a separate workflow. Writes on one connection run one after another,
   because each step takes the connection lock.
4. **Workflow** (`ExecuteActionWorkflow`, id `action-<action_id>`):
   - `start`: `approved` to `running`; checks `ensure_can_run` again
     (writes disabled after approval give `failed`),
   - `write`: `create_account` or `delete_account` under the connection lock
     (waits up to `ACTION_LOCK_WAIT_SECONDS`, then a 5 min limit per call);
     success gives `verifying`. After taking the lock, `ensure_can_run` checks
     `writes_enabled` and the connector once more: turning off "Allow writes" during
     a batch stops the writes that waited in the queue (`failed`,
     "Not written: …"). The activity has **no retries**: a second write could
     create or delete the account a second time,
   - `verify`: `list_accounts` under the same lock, up to `ACTION_VERIFY_ATTEMPTS`
     times (default 3), the first read at once, the next ones every
     `ACTION_VERIFY_DELAY_SECONDS` (default 30). Each failed read is
     `action.verify_attempt` in the audit, the last one gives `failed` with a description, even
     when the write returned 200,
   - activity failure after retries: `fail` with a request to check the account
     by hand.
5. **Confirmation by read**:
   - create: the account is on the list (by `external_id` from the write response,
     then by e-mail) and has the status `active` or `invited`,
   - delete: the account is gone or has the status `suspended` (Google Workspace
     suspends, `Connector.delete_suspends = True`, "Suspend" in the UI).
6. **Accounts after `done`** (`action_accounts.py`): a created account is
   saved (upsert by `external_id`) and assigned to the action's person by hand
   (`match_method = manual`), `action.account_id` points to it. A deleted
   account gets `removed`, a suspended one `suspended`.
7. **`NeedsLogin`** in a write or a read: `failed` with the error
   "Needs login: …" and the connection `needs_login`. Another connector error in a write:
   `failed`, the connection unchanged.
8. **A manual task** is closed by a person (`complete`). A deletion in an app without
   a connection marks the account as `removed`. A creation in an app without
   a connection adds an account from `payload` (e-mail, role) assigned to the person.
   In an app with a connection the next sync confirms the change.

9. **Failed write** (`action_retry.py`, the "Retry" and "Do it by
   hand" buttons in the panel):
   - `retry`: the same conditions as approval (`ensure_can_run`), `failed`
     to `approved`, clears the error and the screenshot, `result.retries` = n, a new workflow
     with id `action-<id>-retry-<n>` and `precheck=True`. The `precheck` step reads
     the account list under the lock: when the app already shows the change (the previous run
     wrote, and failed later), the action ends `done` with
     `result.already_done` without a second write. A read error ends the action
     `failed`: a blind write could land twice,
   - `do_by_hand`: the write becomes an approved `manual_task` with
     `payload.operation`; the error and the screenshot stay as a hint for the person.

**Row lock.** `advance` takes `SELECT … FOR UPDATE` on the action
and reads it again; `approve`, `approve_batch` and the `start` step lock the row
from the first read. Two concurrent approvals give one 200 and one
409, and a cancel at the moment of the start either wins (no write) or gets 409.

Audit: `action.created`, `action.approved` (on a retry with `retry` and `previous_error`, on a change with `manual`), `action.running`,
`action.verifying`, `action.verify_attempt`, `action.done`, `action.failed`,
`action.cancelled`, `action.secret_revealed`, `account.created`,
`account.removed`, `account.suspended`. Each event has `app_id`
and `person_id` (`services/audit.py` takes them from the action or the account).

## Secret from a write (temporary password)

`create_account` can return `CreatedAccount.temporary_password` (Google).
The password goes only to `action.secret_result_encrypted` (Fernet, key
`OPEN_REVOKE_SECRET_KEY`), never to `result`, logs or the audit. `ActionOut`
shows `has_secret_result`. `POST /api/actions/{id}/reveal-secret` returns
the value once (`SELECT … FOR UPDATE`), clears the column and saves
`action.secret_revealed` without the value. A second call: 404.

## How to check by hand

There are no automated tests in the dev phase. You check the path in the local
stack (`compose.dev.yaml`), which sets
`OPEN_REVOKE_ENABLE_FAKE_CONNECTOR=true` and `ACTION_VERIFY_DELAY_SECONDS=1`:

1. In the panel (http://localhost:18410) add a
   `fake` or `browser_fake` connection, turn on "Allow writes", run a sync.
2. Create an action (offboard a person or `POST /api/actions`) and approve it.
3. Check the action status in the panel or in the database:
   `dc exec postgres psql -U postgres -d open_revoke -c "select kind, status, error from action order by created_at desc limit 5"`.
4. When the action is stuck, look at the worker: `dc logs --tail 100 worker`.

The `fake` connector saves creations and deletions in Redis
(`connectors/fake/state.py`, keys `open-revoke:fake-connector:<domain>:*`).
`write_mode = ignore` accepts the write and changes nothing, so verification
ends `failed`. `mode = needs_login` simulates an expired session. The fake
`browser_fake` panel invites (`POST /users`) and removes
(`POST /users/{id}/remove`), state in the keys `open-revoke:fake-panel:*`.
`dc exec api python -m app.db reset` clears Redis together with the database.

## Batches: offboarding and onboarding

Both create actions through `create_action` with one `batch_id`; `approve_batch`
approves them.

- `services/offboarding.py` (`POST /api/people/{id}/offboard`): the person
  gets `left`, each account other than `removed` gets `delete_account`
  or `manual_task`. It skips `service` accounts and accounts with an open deletion.
- `services/onboarding.py` (`POST /api/people/{id}/onboard`, schema
  `OnboardRequest`): each selected app gets `create_account` or
  `manual_task` (`operation = create_account`), `reason = onboarding`.
  It skips apps where the person has an account other than `removed` (`has_account`) and apps with
  an open creation (`action_open`). A `left` person and an unknown app: 400,
  then nothing is saved.

## How to extend

- New connector with writes: add `Capability.CREATE_ACCOUNT` /
  `DELETE_ACCOUNT` and the methods (`skills/backend/new-connector.md`). When deletion
  in the app only suspends, set `delete_suspends = True`.
- New workflow step: a function in `action_execution.py`, an activity in
  `action_activities.py`, a step in `ActionSteps` and `run_action_steps`,
  the executor `_WorkflowSteps` in `temporal/action_workflow.py`.
- New kind of secret: save it encrypted in
  `secret_result_encrypted` and set `result["secret_kind"]`.
