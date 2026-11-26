# open-revoke/backend/app/services/access/

Access requests and who approves them, people's managers, access profiles, and the signed-in user's own access (`/api/me`). Plan of the flow: `skills/backend/actions.md` (actions) and `skills/backend/slack-agent.md` (Slack).

- `__init__.py`: package docstring.
- `requests.py`: `request_access` (a request becomes a `create_account` action or a manual task; `Outcome`, `RequestResult`, `SlackOrigin`), `list_requests`, `close`, `closing_status`.
- `my_access.py`: `person_of`, `overview`, `request`: the signed-in user's accounts, requests and requestable apps.
- `managers.py`: `manager_of`, `emails_of`, `panel_user_of`, `manager_panel_user` (the panel user who decides as a person's manager; None for no manager, a leaver, or no active account).
- `profiles.py`: access profile CRUD (`list_profiles`, `get_profile`, `create_profile`, `update_profile`, `delete_profile`, `get_profile_row`, `app_role_suggestions`) and `auto_approving_profile` (a profile of the person with the app and `auto_approve_requests`, so the request skips the manager). Skill `skills/backend/access-profiles.md`.
- `profile_assignment.py`: `assign_to_person`, `assign_members`: assignment plus one onboarding batch per person with the profile's roles; `dry_run` preview with monthly cost.
- `profile_members.py`: `person_profiles`, `person_drift`, `list_members`, `unassign` (returns `suggested_removals`, deletes nothing in apps).
- `profile_data.py`: bulk loaders (`profile_apps`, `profiles_of`, `grants_of`, `accounts_of`, `creating_of`), `drift_of` (`DriftData.out`), `members_missing_by_profile` (also the dashboard alert), `seat_price`, `profile_app_out`.
- `profile_drift.py`: pure drift rules: `resolve` (role per app from several profiles, `RoleConflict`), `compute` (`missing`, `extra`, `role_mismatch`).
