# ChatGPT connector (Team)

Key: `chatgpt`. Method: browser (admin session in the `browser`
container). Code: `backend/app/connectors/chatgpt/`.

**Status 22.11.2026: not verified.** The endpoints, fields and payloads are
written from knowledge of the chatgpt.com app, without a recording on a real
account. Before use, go through the steps in the section "How to verify". All
addresses are constants at the top of `connector.py`.

ChatGPT Enterprise has SCIM and the Compliance API; there the `scim`
connector is the better choice. The Team plan (since 2025 also named
Business) has no SCIM (not verified for 11.2026).

## Risk: anti-bot protection

chatgpt.com sits behind Cloudflare and has its own protection against
automation. Chromium in Docker (Linux, `--no-sandbox`, Xvfb) can get a
CAPTCHA at sign-in or a "Just a moment..." page on requests. A person signs
in through noVNC, and the requests go from the tab after sign-in. This
helps, but it does not guarantee that the requests get through. An HTML
response instead of JSON ends the sync with an error that names the anti-bot
protection, not with `needs_login`. When this repeats, the app stays `manual`.

## How to connect

1. An app with the `browser` integration, connection `chatgpt`. Leave the
   `account_id` field empty, unless the admin account belongs to several
   workspaces (the error message gives a list with the IDs).
2. Page `/browser`, "Log in" next to ChatGPT: it opens
   `https://chatgpt.com/auth/login`. Sign in with an **Owner or Admin**
   account of the workspace and switch to the company workspace (not the
   personal account).
3. "Check", then "Sync now".

## How it works

The app exchanges the session cookie for a short-lived token in
`GET /api/auth/session` (`accessToken`) and calls `/backend-api` with the header
`Authorization: Bearer <token>` and `ChatGPT-Account-Id: <workspace>`.
The connector does the same from a chatgpt.com tab on every call.

| Operation | Call (not verified) |
|---|---|
| token | `GET /api/auth/session`; no `accessToken` (signed out: `{}`) is `needs_login` |
| workspace | `account_id` from the config or `GET /backend-api/accounts/check/v4-2023-04-27`: the only account with `structure: workspace` or `plan_type` `team`/`business`/`enterprise`/`edu` |
| `check` | `GET /backend-api/accounts/{id}/users?offset=0&limit=1` |
| `list_accounts` | `GET /backend-api/accounts/{id}/users?offset&limit=100` until `total`, `GET /backend-api/accounts/{id}/invites?offset&limit=100` |
| `create_account` | `POST /backend-api/accounts/{id}/invites` with `{"email_addresses": [...], "role": "standard-user", "resend_emails": true}` |
| `delete_account` | member: `DELETE /backend-api/accounts/{id}/users/{user_id}`; invite: `DELETE /backend-api/accounts/{id}/invites` with `{"email_address": …}` |

## Mapping

- Member: `external_id` = `id` (`user-...`), `email`, `display_name` =
  `name`. Role: `account-owner` gives `owner`, `account-admin` gives `admin`,
  `standard-user` gives `member`. `deactivated_time` gives `suspended`.
- Invite: `external_id` = `invite:{id}` (without `id`: `invite:{email}`),
  status `invited`.
- Pagination by `offset` up to `total`. An empty page before `total` ends
  the sync with the error `IncompleteListError`. Without `total`, the
  connector reads while the page is full.
- A `POST .../invites` response with a non-empty `errored_emails` is an action error.

## Limits

- The token from `/api/auth/session` expires. The connector fetches it on
  every call, so it works as long as the session cookie lives.
- Accounts in a workspace with SSO and a verified domain can appear without
  an invite (auto-join); the connector sees them only once they are members.
- Anti-bot protection (above).

## How to verify

1. Sign in to chatgpt.com in noVNC with a workspace admin account.
2. Record the traffic:
   ```bash
   docker compose exec app python -m app.devtools.capture --host chatgpt.com --out captures/chatgpt.jsonl
   ```
   In noVNC: workspace settings (Admin, Members / Users), scroll the member
   list, the invites tab (Pending invites), invite a test address (a
   separate e-mail, not an employee), revoke the invite. Ctrl+C.
3. Check in `captures/chatgpt.jsonl`: the paths and parameters of the lists
   (`offset`, `limit`, `query`), the `items` and `total` fields, the role
   names, the invite body, how an invite is revoked, the headers
   (`ChatGPT-Account-Id`, `OAI-*`). The `Authorization` header and the token
   are masked in the recording.
4. Fix the constants in `connector.py` and `mapping.py`, add a fixture
   (fictional data, `example.com`) and a test. Change "not verified" to the
   date of the check. Delete the recording.
