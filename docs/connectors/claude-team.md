# Claude connector (Team)

Key: `claude`. Method: browser (admin session in the `browser` container).
Code: `backend/app/connectors/claude/`.

**Status 22.11.2026: not verified.** The endpoints, fields and payloads are
written from knowledge of the claude.ai app, without a recording on a real
account. Before use, go through the steps in the section "How to verify". All
addresses are constants at the top of `connector.py`.

Claude Enterprise has SCIM; there the `scim` connector is the better choice.
The Team plan has no SCIM (not verified for 11.2026).

## How to connect

1. An app with the `browser` integration, connection `claude`. Leave the
   `org_uuid` field empty, unless the admin account belongs to several
   Team organizations (the error message gives a list with the IDs).
2. Page `/browser`, "Log in" next to Claude: it opens
   `https://claude.ai/login`. Sign in with an **Owner or Admin** account of
   the organization. Sign-in with an e-mail link or through Google works
   in noVNC as in a normal browser.
3. "Check", then "Sync now".

## How it works

claude.ai authenticates its own API with the session cookie (`sessionKey`),
so `fetch()` from a claude.ai tab is enough. The connector adds the header
`anthropic-client-platform: web_claude_ai` (we do not know if it is required).

| Operation | Call (not verified) |
|---|---|
| organization | `GET /api/organizations`; choice: `org_uuid` from the config or the only organization with the capability `raven` (Team) or `raven_type` `team`/`enterprise` |
| `check` | organization, then `GET /api/organizations/{org}/members` |
| `list_accounts` | `GET /api/organizations/{org}/members` and `GET /api/organizations/{org}/invites` |
| `create_account` | `POST /api/organizations/{org}/invites` with `{"email_address": …, "role": "user"}` (`admin` for the admin role) |
| `delete_account` | member: `DELETE /api/organizations/{org}/members/{account_uuid}`; invite: `DELETE /api/organizations/{org}/invites/{invite_uuid}` |

## Mapping

- Member: `external_id` = `account.uuid`, `email` = `account.email_address`,
  `display_name` = `account.full_name`. Role: `primary_owner` and `owner`
  give `owner`, `admin` gives `admin`, `user` gives `member`. Status `active`.
- Invite: `external_id` = `invite:{uuid}`, status `invited`. Invites
  with a status other than `pending` (accepted, expired) are skipped.
- The parser accepts a list or an object with a list (`members`, `invites`, `data`,
  `items`). A response with `has_more`, `next_cursor` or `next_page` ends the sync
  with the error `IncompleteListError`: we do not know the pagination, and an
  incomplete list would look like deleted accounts.

401 or 403 on `/api/organizations` is `needs_login`. 403 on the member
list is the error "account is not an admin", not `needs_login`.

## Limits

- claude.ai sits behind Cloudflare. An HTML response instead of JSON ends
  the sync with an error that names the sign-in page or the anti-bot
  protection.
- An accepted invite disappears from the invite list and appears as a
  member with a different `external_id`. Sync marks the invite as `removed`.
- Organizations with many thousands of members may have pagination that
  the connector does not support (then an error, not a silent loss of
  accounts).

## How to verify

1. Sign in to claude.ai in noVNC with an admin account.
2. Record the traffic:
   ```bash
   docker compose exec app python -m app.devtools.capture --host claude.ai --out captures/claude.jsonl
   ```
   In noVNC: organization settings, the members tab (Members), scroll the
   list to the end, invite a test address (a separate e-mail, not an
   employee), revoke the invite. Ctrl+C.
3. Check in `captures/claude.jsonl`: the paths of the member and invite
   lists, the pagination (parameters `offset`, `limit`, `cursor`), the
   invite body, the method and path of the deletion, the role names, the
   field with the Team plan capability in `/api/organizations`, the
   required headers.
4. Fix the constants in `connector.py` and `mapping.py`, add a fixture
   (fictional data, `example.com`) and a test. Change "not verified" to the
   date of the check. Delete the recording.
