# open-revoke/backend/app/mcp/agent/

Task tools of the MCP server (the default toolset): one tool per task an admin or a member asks, each composing a few API calls through `AgentApi` with the caller's token. Skill `skills/backend/mcp.md`, "Adding a task tool".

- `__init__.py`: empty.
- `base.py`: `AgentTool` (name, title, description, input schema, handler, `read_only`, `destructive`, `audience` admin or user), `ToolError` (message for the assistant), `schema()`, shared `PERSON_ARG`, `APP_ARG`.
- `api.py`: `AgentApi` (`get`, `post`, `patch`, `put` on `/api/...`, errors as `ToolError`; `apps()`, `person(reference)`, `app(reference)`, `discovered_app(reference)` resolve an e-mail, name, slug or id to one record or list the candidates), `match_app`, `PAGE_LIMIT`.
- `views.py`: compact shapes: `person_line`, `account_line`, `action_line`, `money`, `removal` (how offboarding removes an account, from the app's `delete_mode`).
- `apps.py`: `get_overview`, `get_spend_by_app`, `get_app_access`, `add_app` (catalog match), `update_app` (price, request policy).
- `people.py`: `find_people`, `get_person_access`, `list_leavers_with_access`, `add_person`, `update_person`.
- `offboarding.py`: `plan_offboarding` (no writes), `start_offboarding` (destructive).
- `onboarding.py`: `onboard_person` (destructive), `list_access_profiles`, `assign_access_profile` (`dry_run` by default), `get_access_drift`.
- `actions.py`: `list_pending_approvals`, `approve_actions` (destructive), `cancel_actions`, `get_actions_status` (by `batch_id` or `action_ids`), `list_open_manual_tasks`, `complete_manual_task`, `list_failed_actions`, `retry_action`.
- `accounts.py`: `list_unassigned_accounts`, `assign_account` (owner, service account, role), `add_account` (kept by hand).
- `connections.py`: `list_connectors`, `connect_app` (sets the app's integration, keeps stored settings, checks), `check_connection`, `sync_app`, `get_sync_history`.
- `discovery.py`: `list_discovered_apps`, `get_discovered_app_users`, `track_discovered_app`, `ignore_discovered_app`, `run_discovery_scan`.
- `requests.py`: `list_access_requests`, `decide_access_request`, `get_audit_log`; `request_line`.
- `me.py`: member tools (`audience="user"`): `get_my_access`, `request_access`, `list_my_approvals`, `decide_my_approval`.
- `registry.py`: `MODULES` (listing order), `AGENT_TOOLS`, `call(tool, api, arguments)` (checks arguments; a `ToolError` or an unexpected shape becomes a tool error; JSON text result).
