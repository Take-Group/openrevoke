# open-revoke/backend/app/services/access/

Access requests and who approves them, people's managers, access profiles, and the signed-in user's own access (`/api/me`). Plan of the flow: `skills/backend/actions.md` (actions) and `skills/backend/slack-agent.md` (Slack).

- `__init__.py`: package docstring.
- `requests.py`: `request_access` (a request becomes a `create_account` action or a manual task; `Outcome`, `RequestResult`, `SlackOrigin`), `list_requests`, `close`, `closing_status`.
- `my_access.py`: `person_of`, `overview`, `request`: the signed-in user's accounts, requests and requestable apps.
- `managers.py`: `manager_of`, `emails_of`, `panel_user_of`, `manager_panel_user` (the panel user who decides as a person's manager; None for no manager, a leaver, or no active account).
- `profiles.py`: access profiles; `auto_approving_profile` (a profile of the person with the app and `auto_approve_requests`, so the request skips the manager).
