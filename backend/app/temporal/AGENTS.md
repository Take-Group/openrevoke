# open-revoke/backend/app/temporal/

Temporal layer: a workflow only calls activities, an activity only calls one service in `app/services/`, a `*_dispatcher.py` starts workflows for the API, a `*_schedule(s).py` keeps Temporal Schedules. Task queue is `settings.temporal_task_queue` (`open-revoke`). Inputs are plain dataclasses in `*_types.py` (safe in the workflow sandbox).

- `worker.py`: `start_worker()` registers all 6 workflows and the activity lists; after start runs `reconcile_schedules()` (sync schedule per connection, scan schedule per discovery connection), `ensure_rates()`, `ensure_update_check()`, `connect_browser()`, then `SlackAgentRunner(...).run_forever()` (the Slack agent runs inside the worker process). Entry `run()`.
- `client.py`: `get_temporal_client()`, cached client from settings.
- `sync_workflow.py`: `SyncConnectionWorkflow`: `start_sync_run`, then `run_sync` (30 min, 3 retries), on crash `fail_sync_run`. Started by "Sync now" and the schedule.
- `sync_activities.py`: `start_sync_run`, `run_sync`, `fail_sync_run` (list `SYNC_ACTIVITIES`) call `services/sync.py`.
- `sync_types.py`: `SyncParams`, `RunSyncInput`, `FailSyncInput`.
- `dispatcher.py`: `TemporalSyncDispatcher` (`start_sync` with id `sync-run-<id>`, `upsert_schedule`, `delete_schedule`), `get_sync_dispatcher()`; implements `services/sync_dispatch`.
- `schedules.py`: schedule `sync-connection-<id>` every `SYNC_INTERVAL_HOURS` with jitter: `upsert_sync_schedule`, `delete_sync_schedule`, `reconcile_sync_schedules`.
- `scan_workflow.py`: `ScanConnectionWorkflow`: one app-discovery scan of one connection (start, run, fail like sync).
- `scan_activities.py`: `start_scan_run`, `run_scan`, `fail_scan_run` (`SCAN_ACTIVITIES`) call `services/discovery_scan.py`.
- `scan_types.py`: `ScanParams`, `RunScanInput`, `FailScanInput`.
- `scan_dispatcher.py`: `TemporalScanDispatcher`, `get_scan_dispatcher()`; implements `services/scan_dispatch`.
- `scan_schedules.py`: schedule `scan-connection-<id>` every `SCAN_INTERVAL_HOURS`: `upsert_scan_schedule`, `reconcile_scan_schedules`.
- `action_workflow.py`: `ExecuteActionWorkflow`: one approved write action. Step order lives in `services/action_flow.run_action_steps` (start, precheck on a retry, write, verify attempts). The write activity is never retried (a second create or delete could hit the app twice); a crash ends the action as failed via `fail_action`.
- `action_activities.py`: `start_action`, `precheck_action`, `write_action`, `verify_action`, `fail_action` (`ACTION_ACTIVITIES`) call `services/action_execution.py`.
- `action_types.py`: `ExecuteActionParams` (`precheck` for a retry), `VerifyActionInput`, `FailActionInput`.
- `action_dispatcher.py`: `TemporalActionDispatcher.start_action` (id `action-<id>`, a retry `action-<id>-retry-<n>`); implements `services/action_dispatch`; sets the activity timeout from `WRITE_TIMEOUT_SECONDS`/`FETCH_TIMEOUT_SECONDS` plus a margin.
- `google_setup_workflow.py`: `GoogleCloudSetupWorkflow`: automatic Google Cloud setup, one browser run (25 min).
- `google_setup_activities.py`: `run_google_cloud_setup` (heartbeats every 10 s) calls `services/google_cloud_setup/runner.py` (`GOOGLE_SETUP_ACTIVITIES`).
- `google_setup_dispatcher.py`: `start_google_cloud_setup()`, fixed workflow id `google-cloud-setup` so only one runs.
- `rates_workflow.py`: `RefreshExchangeRatesWorkflow`: download today's exchange rates.
- `rates_activities.py`: `refresh_exchange_rates` (`RATES_ACTIVITIES`) calls `services/exchange_rates.py`.
- `rates_schedule.py`: schedule `exchange-rates-daily` (cron `30 2 * * *`): `upsert_rates_schedule`; `ensure_rates()` also downloads at worker start when today's rates are missing.
- `update_check_workflow.py`: `CheckForUpdateWorkflow`: newest stable release from GitHub.
- `update_check_activities.py`: `check_for_update` (`UPDATE_CHECK_ACTIVITIES`) calls `services/update_check.py`.
- `update_check_schedule.py`: schedule `update-check-hourly` (every hour, 30 min jitter): `ensure_update_check()` upserts it and checks once at worker start, or deletes it when the check is off.
- `__init__.py`: empty.
