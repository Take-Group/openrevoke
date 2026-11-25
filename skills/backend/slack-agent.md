# Skill: Slack agent and AI model settings

## What it does

A Slack bot that takes access requests in direct messages. A person writes
"I need Notion"; the language model finds the app, creates a
`create_account` action (or a manual task) for that person and says what
happens next. When the action ends, the bot tells the person on Slack.
Admins on Slack get requests that wait for approval with Approve and Reject
buttons. Setup is on the panel page `/settings/slack`; the requests (from Slack and
from My access) are on `/requests`.

The model is chosen on `/settings/ai`, shared by every AI feature of the panel:
Anthropic (official `anthropic` SDK, default `claude-opus-5-5`), OpenAI,
OpenRouter, or any OpenAI-compatible endpoint with its own base URL and key
(`openai` SDK). The admin first connects (provider, key, base URL; "Connect"
calls `POST /api/ai-settings/models`, which lists the provider's real models),
then picks a model from that list and a reasoning level: the levels the
Anthropic Models API reports for the model, OpenRouter's `reasoning` support,
or low/medium/high where the provider does not say (OpenAI, custom). "Model
default" sends no effort. Anthropic gets `output_config.effort`, OpenRouter
`reasoning.effort`, the rest `reasoning_effort`.

## Files

| File | What it does |
|---|---|
| `backend/app/ai/base.py` | `LanguageModel` protocol, `ToolSpec`, `ChatTurn`, `ToolError`, `AiError`, `MAX_TOOL_ROUNDS` |
| `backend/app/ai/anthropic_model.py` | Messages API tool loop; appends each response unchanged; `fallbacks: "default"` on models that take it |
| `backend/app/ai/openai_compatible.py` | Chat Completions tool loop for OpenAI, OpenRouter and custom endpoints |
| `backend/app/ai/factory.py` | provider catalog for the panel (`PROVIDERS`), `build_model` |
| `backend/app/services/ai_settings.py`, `api/ai.py` | `ai_settings` row (key encrypted), model list, test call, `load_model` for the runtime |
| `backend/app/models/slack_agent.py` | one row: app id, team, bot user, status, encrypted tokens |
| `backend/app/services/slack_agent_secrets.py` | token keys in `secrets_encrypted`, configuration token rotation |
| `backend/app/services/slack_agent_setup.py`, `api/slack_agent.py` | create the app from the manifest, set the icon, OAuth install, paste tokens, on/off, remove |
| `backend/app/slack_agent/manifest.py` | bot scopes, `message.im`, Socket Mode, interactivity, OAuth redirect (https panels only) |
| `backend/app/slack_agent/avatar.py`, `assets/avatar.png` | default icon, 1024 px |
| `backend/app/slack_agent/runner.py` | runs in the Temporal worker process: (re)starts Socket Mode when tokens change, polls approvals and results every 10 s |
| `backend/app/slack_agent/socket_mode.py` | `apps.connections.open`, WebSocket, ack every envelope at once, reconnect with backoff |
| `backend/app/slack_agent/events.py` | DMs to the bot (deduplicated by `event_id`) and button clicks |
| `backend/app/slack_agent/conversation.py` | person lookup, placeholder message, model call, history in Redis (20 turns, 24 h) |
| `backend/app/slack_agent/tools.py` | `list_apps`, `my_access`, `request_access`; the requester comes from Slack, never from the model |
| `backend/app/slack_agent/prompt.py`, `texts.py` | system prompt; fixed messages (unknown person, results) |
| `backend/app/slack_agent/identity.py` | Slack user to person (Slack connector account, then profile e-mail) and to panel admin |
| `backend/app/slack_agent/approvals.py`, `notifier.py` | Approve / Reject messages to admins; result messages to people |
| `backend/app/services/access_requests.py` | the request: policy, duplicate checks, action, auto-approval |
| `backend/app/models/access_request.py` | request row: person, app, action, Slack channel, notified times |
| `frontend/src/components/ai/*`, `hooks/use-ai-settings.ts`, `lib/api/ai-types.ts` | `/settings/ai` |
| `frontend/src/components/slack/*`, `hooks/use-slack-agent.ts`, `lib/api/slack-types.ts` | `/settings/slack` |
| `backend/app/api/access_requests.py`, `frontend/src/components/requests/*`, `hooks/use-access-requests.ts` | `/requests` |

## Data flow

1. A DM arrives over Socket Mode. `events.is_direct_message` drops bot
   messages, edits and joins; Redis `SET NX` on `event_id` drops retries.
2. `identity.find_person`: an account of the `slack` connector with
   `external_id` = Slack user id, else the Slack profile e-mail matched to a
   primary e-mail or alias. Unknown or `left` people get a fixed answer and
   no model call.
3. The model answers with the tools. `request_access` calls
   `services.access_requests.request_access`:
   - `app.self_service = off`: refused,
   - account or open creation exists: nothing new,
   - else `create_action(reason=self_service)` and an `access_request` row,
   - `automatic`: `action_approval.approve` at once. A connector write
     starts `ExecuteActionWorkflow`; without "Allow writes" the action stays
     pending; a manual task waits for an admin.
4. The runner's poll (`approvals.notify_pending`) sends pending requests to
   every panel admin whose e-mail has a Slack account. A click is checked
   against the panel admin list and approves or cancels the action; the audit
   actor is `<admin e-mail> (Slack)`.
5. `notifier.notify_finished` closes requests whose action is `done`,
   `failed` or `cancelled` and messages the person. A failed post keeps the
   request open for the next poll, except for unreachable channels.

## Setup limits (Slack, checked 23.11.2026)

- `apps.manifest.create` needs an app configuration token
  (`xoxe.xoxp-…`, 12 h, generated at the bottom of api.slack.com/apps). Its
  refresh token lets `tooling.tokens.rotate` renew it for later icon changes.
- `apps.icon.set` takes the same token; 512-2000 px images. An app created
  by hand from the manifest link cannot get its icon from Open Revoke.
- No API creates the app-level token (`xapp-`, scope `connections:write`):
  the admin generates it in Basic Information and pastes it.
- OAuth install (`/api/slack-agent/oauth/start` and `/callback`) works only
  when `PUBLIC_URL` is https; otherwise the admin installs from the app page
  and pastes the bot token. Both paths verify tokens with `auth.test` and
  `apps.connections.open` before saving.

## How to check by hand

No real Slack workspace or model key is needed for the flow itself: run a
script in the `api` container that replaces `app.slack_agent.web_api.call`
and `conversation.load_model` with fakes and feeds envelopes to
`events.handle_envelope` (DM, then a `block_actions` click), then calls
`approvals.notify_pending` and `notifier.notify_finished`. With the `fake`
connector, "Allow writes" and `self_service = automatic`, a request runs the
real workflow to `done`. Bad tokens show in the panel as status `error`
within 10 s (`dc logs --tail 50 worker`).

## Open items (state on 23.11.2026)

Built and checked with a fake Slack API and a fake model only. Before the
bot goes to a real workspace:

1. **Live run on a test workspace.** Create the app with a configuration
   token, install it, paste the `xapp-` token, write to the bot, approve with
   the buttons, get the result message. Nothing of this ran against real
   Slack yet; only bad-token errors were seen from the real API.
2. **Unverified Slack assumptions** (fix in one place each if wrong):
   - the manual link `https://api.slack.com/apps?new_app=1&manifest_json=…`
     opens the app form filled from the manifest (`SlackAgentOut.manifest_url`),
   - `auth.test` with a bot token returns `app_id` (`_save_bot_token`); if not,
     an app created by hand has no `app_id` and no install link,
   - Slack accepts the OAuth redirect only on https (`manifest.oauth_redirect_url`),
   - an icon set before the install may be ignored; `finish_oauth` sets it
     again, the paste-token path does not,
   - the bot can open a DM with `chat.postMessage` to a user id (`approvals`).
3. **Real model runs.** Tool calling with an Anthropic key, OpenAI, OpenRouter
   and a custom endpoint. Custom endpoints without tool support fail with the
   provider's 400; the panel's "Test" does not call tools.
4. **Language of fixed messages.** `texts.py` is English; the model answers in
   the person's language. Needs a language setting or the language of the
   request.
5. **Stale buttons.** A request approved or rejected in the panel keeps the
   Approve / Reject buttons in the admins' Slack messages (a click then says
   "Not done"). Update those messages when the action changes.
6. **Failures to admins.** A failed request only tells the person; admins see
   it in the panel. Send it to the admins on Slack too.
7. **Limits and cost.** No per-person rate limit and no token budget for the
   model; history is in Redis only (24 h). The default model
   `claude-opus-5-5` is expensive for a chat bot.
8. **App changes after setup.** A new bot name needs `apps.manifest.update`;
   "Remove" only forgets the app (could call `apps.manifest.delete`).
9. **Scope.** Requests create accounts only. No role changes, no "remove my
   access", no requests for other people (on purpose).
10. **One worker.** The runner lives in the worker process. Several workers
    open several Socket Mode connections (Slack allows up to 10) and poll
    with `SKIP LOCKED`, which should hold, but was not tried.

## How to extend

- New tool: a `ToolSpec` in `TOOLS` and a branch in `AgentTools.execute`.
  Keep the requester fixed; write tools must go through services with
  `audit.record`.
- New provider: a `LanguageModel` implementation in `app/ai/`, an
  `AiProvider` value, a `ProviderInfo` row and a branch in `build_model`.
- New Slack event: a bot event in `manifest.BOT_EVENTS` (existing apps need
  the scope or event added in Slack) and a branch in `events.handle_envelope`.
