# Skill: New connector and account sync

## What it does

A connector talks to one SaaS app: it reads accounts (and optionally people),
creates them and deletes them. It does not write to the database. Sync (`SyncConnectionWorkflow`)
calls the connector and stores the result.

## Files

| File | What it does |
|---|---|
| `backend/app/connectors/base.py` | `Connector` (ABC), `Capability`, `AuthKind`, `RemoteAccount`, `RemotePerson`, `CreateAccountRequest`, `CreatedAccount`, `CheckResult`, `ConnectorContext`, `SecretField` |
| `backend/app/connectors/errors.py` | exceptions `ConnectorError`, `NeedsLogin`, `IncompleteListError` |
| `backend/app/connectors/registry.py` | list of connectors, `get_connector`, `all_connectors`; `fake` only with `DEBUG` or `OPEN_REVOKE_ENABLE_FAKE_CONNECTOR=true` |
| `backend/app/connectors/http.py` | `build_http_client` (timeout, log without query and headers), `raise_for_app_error` (401 is `NeedsLogin`), `check_page_limit` |
| `backend/app/connectors/<key>/connector.py` | connector class and `config_schema` model |
| `backend/app/connectors/<key>/mapping.py` | pure functions: JSON response to `RemoteAccount` / `RemotePerson` |
| `backend/app/services/secret_box.py` | Fernet encryption of secrets (`OPEN_REVOKE_SECRET_KEY`) |
| `backend/app/services/connector_runtime.py` | `open_context`: decryption, config validation, HTTP client |
| `backend/app/services/connections.py` | catalog, saving a connection (split into config and secrets), `check`, `set_status` |
| `backend/app/services/sync.py` | sync run: `start_run`, `run`, `fail_run` |
| `backend/app/services/sync_accounts.py`, `sync_rules.py`, `people_sync.py` | saving accounts, matching, vanished accounts, 30% threshold, people source |
| `backend/app/services/connection_lock.py` | Redis lock by `connection_id` |
| `backend/app/services/sync_requests.py`, `sync_dispatch.py` | "Sync now" from the API, `SyncDispatcher` interface |
| `backend/app/temporal/sync_workflow.py`, `sync_activities.py`, `sync_types.py` | workflow, activities and their inputs |
| `backend/app/temporal/schedules.py`, `dispatcher.py`, `worker.py` | Schedule per connection, starting the workflow, reconciling schedules when the worker starts |
| `backend/app/api/connections.py` | `GET /api/connectors`, `PUT /api/apps/{id}/connection`, `.../check`, `.../sync`, `GET .../sync-runs` |
| `backend/app/connectors/browser_api.py` | `BrowserSession` for browser connectors, `BrowserResponse`, `raise_for_browser_error`, `browser_json` |
| `docs/connectors/<key>.md` | how to connect, endpoints, limits |

## Sync flow

1. `POST /api/apps/{id}/connection/sync` creates a `sync_run` (`running`),
   commits and starts `SyncConnectionWorkflow` (id `sync-run-<run>`).
   The schedule `sync-connection-<connection>` starts the same workflow every
   `SYNC_INTERVAL_HOURS` without a `sync_run`; the activity `start_sync_run` creates it
   itself.
2. The activity `run_sync` takes the connection lock. If the lock is taken: the run is `failed`,
   the connection status does not change.
3. Read without an open transaction: `list_people` (when `is_people_source`
   and the connector has `LIST_PEOPLE`), then `list_accounts`, and with `READ_BILLING` also
   `read_billing` (`BillingInfo`; an error goes only to the log, the account sync continues;
   saved by `services/billing.py`). Limit 20 minutes.
4. `NeedsLogin`: the run and the connection are `needs_login`. Any other connector error: the run is
   `failed`, the connection is `error`. Accounts do not change in either case.
5. Write in one transaction: people (`people_sync.py`; `RemotePerson.manager_email`
   is resolved to a person in a second pass, `department` and `job_title` are
   stored as they come), then accounts
   (`sync_accounts.py`). Too many vanished accounts (more than 30% of the accounts other
   than `removed`) roll back the whole transaction; `?force=true` skips the threshold.
6. Audit: `account.discovered`, `account.reappeared`,
   `account.changed_in_app`, `account.removed_detected`, `account.matched`,
   `account.unmatched`, `person.created`, `person.updated`,
   `connection.status_changed`, `sync.forced`.

## How to add a connector

1. Folder `backend/app/connectors/<key>/` with `__init__.py`, `connector.py`,
   `mapping.py`.
2. `config_schema`: a Pydantic model. A secret field is a `SecretStr` with
   `SecretField(title=...)`. The JSON Schema gets `"secret": true`,
   `"format": "password"`, `"writeOnly": true`; `multiline=True` adds
   `"x-multiline": true`. Saving the connection separates secrets from the config by itself.
3. The class inherits from `Connector`. Set `key`, `display_name`,
   `integration`, `auth_kind`, `capabilities`, `config_schema`,
   and optionally `login_url` and `admin_url`. Implement `check`,
   `list_accounts` and the methods from `capabilities`.
4. In the methods, type the context as `ConnectorContext[YourConfig]`; read secrets
   with `ctx.config.<field>.get_secret_value()`. Send requests only through `ctx.http`.
   After every response call `raise_for_app_error(response, NAME)`.
5. Pagination: a loop with `check_page_limit`. When you cannot confirm the full
   list, raise `IncompleteListError`. Never return part of a list.
6. `mapping.py`: pure functions without I/O. Put only the needed fields into `raw`,
   without phone numbers, addresses and tokens.
7. Add the instance to `_PRODUCTION` in `registry.py`.
8. Check by hand in the local stack (there are no automated tests in the dev phase):
   add a connection in the panel (http://localhost:18410),
   run "Sync now", look at the accounts in the panel or with
   `dc exec postgres psql -U postgres -d open_revoke -c "select email, status from account order by email"`, and at errors
   in `dc logs --tail 100 worker`. Dumps of real responses do not go into the
   repository: they contain real people and tokens.
9. `docs/connectors/<key>.md`: where to get the credentials, scopes,
   endpoints, limits. Mark paths not checked on a real account as
   "not verified".
10. Refresh `docs/openapi.json` when you change API schemas.

Browser connectors (Slack, Claude, ChatGPT, `browser_fake`):
`integration = Integration.BROWSER`, `auth_kind = AuthKind.BROWSER_SESSION`,
`login_url`, `admin_url`. `connector_runtime.open_context` gives them
`ctx.browser` (`BrowserSession` from `app/connectors/browser_api.py`). Requests
go through `ctx.browser.fetch(...)` instead of `ctx.http`, errors through
`raise_for_browser_error` and `browser_json`. You find the panel endpoints by
recording traffic (`python -m app.devtools.capture`) and keep them as constants at the
top of `connector.py`. Details and traps: `skills/backend/browser.md`. An unavailable browser ends the sync with an error
(`BrowserUnavailableError`), not `needs_login`.

Docs file name: `docs/connectors/<key>.md`, except for the
`claude` connector: `docs/connectors/claude-team.md`. On macOS (a file system without
case sensitivity) `claude.md` is the same file as `CLAUDE.md`,
which Claude Code reads as the folder instructions.

Write: `create_account` returns `CreatedAccount` (the Google temporary password
goes encrypted into the action and is shown once). `ExecuteActionWorkflow`
calls it after approval, under the same lock
(`connection_lock`) as sync, and a fresh
`list_accounts` confirms the result. A connector that only suspends the account on delete sets
`delete_suspends = True` (Google Workspace). Details:
`skills/backend/actions.md`.

## Checking without real data

The `browser_fake` connector does the same through a real browser on a
fake panel inside the app (`skills/backend/browser.md`).

The `fake` connector (`backend/app/connectors/fake/`) returns fixed accounts
`user<N>@<domain>` and a bot without an e-mail. `mode` = `needs_login` or `error`
simulates a failure. It can also create and delete accounts; it keeps the writes in Redis
(`state.py`), and `write_mode = ignore` accepts a write without changes (verification
ends as `failed`). The local dev stack (`compose.dev.yaml`) turns it on
by itself (`OPEN_REVOKE_ENABLE_FAKE_CONNECTOR=true`). With `compose.yaml`, set this
variable in `.env` and run `docker compose up -d --build`.

## The `target_fields` field

`target_fields` in the connector class lists the config fields that point to the
organization that writes go to (GitHub org, Google domain, Slack
workspace). By default these are all config fields. A change to any of them when
the connection is saved turns writes off and sets the state `never_synced`. Writes can
be turned on again only after a new successful sync. Exclude test fields that do not change
the target from the list (see the `fake` connector).
