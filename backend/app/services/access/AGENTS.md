# open-revoke/backend/app/services/access/

Access requests and who approves them, people's managers, access profiles, and the signed-in user's own access (`/api/me`). The request flow: `skills/backend/access-requests.md`; actions: `skills/backend/actions.md`; Slack: `skills/backend/slack-agent.md`.

- `__init__.py`: package docstring.
- `outcomes.py`: `Outcome` (incl. `waiting_for_manager`), `RequestResult`, `SlackOrigin`: what asking returns, shared by the services, the panel and the Slack agent.
- `requests.py`: `NewRequest`, `request_access` (checks: leaver, policy off, justification 400, account, open request 409; stores the request and calls `flow.route`), `open_request`.
- `flow.py`: `route` (first step by `request_policy`: automatic, admin, manager with profile / on-behalf / fallback reasons), `decide` (a decision on the step a request waits for; 403 own request or not the approver, 409 closed step, comment required to reject), `Decider`.
- `request_sync.py`: `on_action_changed`, called by `actions.advance`: the admin step through `/actions`, done, failed, cancelled, retry.
- `decisions.py`: `record_decision` (row plus audit event), `record_event`, `close`, `CLOSED_STATUSES`, `person_id_of_user`, `ensure_not_own`, `last_rejection`, `people_by_id`. Imports no action service (used by `request_sync`).
- `queries.py`: `RequestFilter`, `list_requests`, `count`, `present` (rows to `AccessRequestOut`), `get_request`, `detail` (decisions, action, seat cost), `decisions_of`, `export_csv`, `waiting_for`.
- `my_access.py`: `person_of`, `overview`, `requestable` (policy, role suggestions), `request` (for oneself or a report), `team`.
- `my_approvals.py`: `list_mine`, `detail`, `decide`: `/api/me/approvals` for a manager (403 outside their reports).
- `slack_reach.py`: `bot_token`, `slack_user_id`: whether a person can decide or hear results on Slack.
- `managers.py`: `manager_of`, `emails_of`, `panel_user_of`, `manager_panel_user` (the panel user who decides as a person's manager; None for no manager, a leaver, or no active account).
- `profiles.py`: access profile CRUD (`list_profiles`, `get_profile`, `create_profile`, `update_profile`, `delete_profile`, `get_profile_row`, `app_role_suggestions`) and `auto_approving_profile` (a profile of the person with the app and `auto_approve_requests`, so the request skips the manager). Skill `skills/backend/access-profiles.md`.
- `profile_assignment.py`: `assign_to_person`, `assign_members`: assignment plus one onboarding batch per person with the profile's roles; `dry_run` preview with monthly cost.
- `profile_members.py`: `person_profiles`, `person_drift`, `list_members`, `unassign` (returns `suggested_removals`, deletes nothing in apps).
- `profile_data.py`: bulk loaders (`profile_apps`, `profiles_of`, `grants_of`, `accounts_of`, `creating_of`), `drift_of` (`DriftData.out`), `members_missing_by_profile` (also the dashboard alert), `seat_price`, `profile_app_out`.
- `profile_drift.py`: pure drift rules: `resolve` (role per app from several profiles, `RoleConflict`), `compute` (`missing`, `extra`, `role_mismatch`).
