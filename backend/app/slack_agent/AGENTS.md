# open-revoke/backend/app/slack_agent/

Slack agent: a Slack app that takes access requests in direct messages. Setup is in the panel (`services/slack_agent_setup.py`); at runtime `runner.py` runs inside the Temporal worker process, one Socket Mode connection (no public URL). A message goes to the language model (`app/ai/`) with three tools; admins approve on Slack.

- `__init__.py`: module docstring only, the overview of setup and runtime.
- `runner.py`: `SlackAgentRunner(dispatcher).run_forever()`: every `POLL_SECONDS` (10) reads `SlackAgent` row (row id 1) and tokens; restarts or stops Socket Mode when tokens, bot name or "off" change; while connected calls `notify_pending` and `notify_finished`.
- `runtime.py`: `SlackRuntime` dataclass (tokens, bot user id, action dispatcher) handed to every handler.
- `socket_mode.py`: `SocketModeConnection`: `apps.connections.open`, acks each envelope at once (Slack retries after 3 s), handles it in a background task, reconnects on `disconnect`.
- `events.py`: `handle_envelope` routes direct messages (`is_direct_message`) and button clicks; dedupes by event id in Redis.
- `conversation.py`: `handle_message`: finds the person, posts a placeholder, asks the model, replaces the placeholder; history of last turns in Redis for a day; one answer at a time per Slack user.
- `identity.py`: `find_person` (by Slack account external id, then by profile e-mail or alias), `find_admin`, `slack_email`, `slack_user_for_email` (cached in Redis).
- `tools.py`: `AgentTools`: model tools `list_apps`, `my_access`, `request_access` (calls `services/access/requests.request_access`); the requester comes from the Slack user, never from model arguments.
- `prompt.py`: `system_prompt`, `Requester`; same text for every turn of one person so prompt caching works.
- `texts.py`: fixed messages without the model: `WORKING`, `UNKNOWN_PERSON`, `NO_MODEL`, `finished`, `approval_request`.
- `approvals.py`: `notify_pending` sends requests waiting for approval to admins with Approve and Reject buttons; `handle_click` accepts a click only from a panel admin with a Slack account, audit log names them.
- `notifier.py`: `notify_finished` tells the requester when the action is done, failed or cancelled; a panel request (`channel` panel) is only closed, not posted.
- `manifest.py`: `build_manifest(bot_name)`, `BOT_SCOPES`, `BOT_EVENTS`, `oauth_redirect_url`.
- `avatar.py`: `default_avatar`, `image_type`; icon limits for Slack `apps.icon.set`.
- `web_api.py`: `call(method, ...)` Slack Web API over httpx (`ok: false` raises `SlackApiError`, retries on rate limit), `SlackApiError`.
- `assets/`, no map: `avatar.png` (default app icon).
