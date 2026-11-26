# open-revoke/backend/app/mcp/agent/

Task tools of the MCP server (the default toolset, admins): one tool per question an admin asks, each composing a few API calls through `AgentApi` with the caller's token. Skill `skills/backend/mcp.md`, "Adding a task tool".

- `__init__.py`: empty.
- `base.py`: `AgentTool` (name, title, description, input schema, handler, `read_only`, `destructive`), `ToolError` (message for the assistant), `schema()`, shared `PERSON_ARG`, `APP_ARG`.
- `api.py`: `AgentApi` (`get`, `post` on `/api/...`, errors as `ToolError`; `apps()`, `person(reference)` and `app(reference)` resolve an e-mail, name, slug or id to one record or list the candidates), `PAGE_LIMIT`.
- `views.py`: compact shapes: `person_line`, `account_line`, `action_line`, `money`, `removal` (how offboarding removes an account, from the app's `delete_mode`).
- `apps.py`: `get_overview`, `get_spend_by_app`, `get_app_access`, `list_discovered_apps`.
- `people.py`: `find_people`, `get_person_access`, `list_leavers_with_access`.
- `offboarding.py`: `plan_offboarding` (no writes), `start_offboarding`, `approve_offboarding` (both destructive), `get_offboarding_status`, `list_pending_approvals`.
- `registry.py`: `AGENT_TOOLS` in listing order, `call(tool, api, arguments)` (checks arguments, JSON text result).
