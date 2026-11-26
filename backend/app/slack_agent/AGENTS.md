# open-revoke/backend/app/slack_agent/

Slack agent: a Slack app that takes access requests in direct messages. Setup is in the panel (`services/slack_agent_setup.py`); at runtime `runner.py` runs inside the Temporal worker process, one Socket Mode connection (no public URL). A message goes to the language model (`app/ai/`) with three tools; managers and admins approve on Slack.

- `__init__.py`: module docstring only, the overview of setup and runtime.
- `runner.py`: `SlackAgentRunner(dispatcher).run_forever()`: every `POLL_SECONDS` (10) reads `SlackAgent` row (row id 1) and tokens; restarts or stops Socket Mode when tokens, bot name or "off" change; while connected calls `notify_pending` and `notify_finished`.
- `runtime.py`: `SlackRuntime` dataclass (tokens, bot user id, action dispatcher) handed to every handler.
- `socket_mode.py`: `SocketModeConnection`: `apps.connections.open`, acks each envelope at once (Slack retries after 3 s), handles it in a background task, reconnects on `disconnect`.
- `events.py`: `handle_envelope` routes direct messages (`is_direct_message`) and button clicks; dedupes by event id in Redis.
- `conversation.py`: `handle_message`: finds the person, posts a placeholder, asks the model, replaces the placeholder; history of last turns in Redis for a day; one answer at a time per Slack user.
- `identity.py`: `find_person` (by Slack account external id, then by profile e-mail or alias), `slack_email`, `slack_user_for_email(bot_token, email)` (both cached in Redis).
- `tools.py`: `AgentTools`: model tools `list_apps`, `my_access`, `request_access` (needs `justification`; calls `services/access/requests.request_access`); the requester comes from the Slack user, never from model arguments.
- `prompt.py`: `system_prompt`, `Requester`; same text for every turn of one person so prompt caching works.
- `texts.py`: fixed messages without the model: `WORKING`, `UNKNOWN_PERSON`, `NO_MODEL`, `UNKNOWN_DECIDER`, `finished` (rejected with the comment), `approval_request` (manager or admin step).
- `approvals.py`: `notify_pending` sends requests by step (manager's Slack for `pending_manager`, admins except the requester for `pending_admin`) with Approve and Reject buttons (value: request id); `handle_click` turns a click into `flow.decide` (`via=slack`).
- `notifier.py`: `notify_finished` tells the requester, for every channel, how a request closed in the last day ended (Slack chat, else a DM by e-mail); closing is in `services/access/request_sync.py`.
- `manifest.py`: `build_manifest(bot_name)`, `BOT_SCOPES`, `BOT_EVENTS`, `oauth_redirect_url`.
- `avatar.py`: `default_avatar`, `image_type`; icon limits for Slack `apps.icon.set`.
- `web_api.py`: `call(method, ...)` Slack Web API over httpx (`ok: false` raises `SlackApiError`, retries on rate limit), `SlackApiError`.
- `assets/`, no map: `avatar.png` (default app icon).
