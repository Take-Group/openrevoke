# Slack connector

Key: `slack`. Method: browser (admin session in the `browser` container).
Code: `backend/app/connectors/slack/`.

**Status 25.11.2026: read checked on a real workspace (Pro plan).**
`auth.test` and `users.list` work; the member count matches the admin
panel. Writes go through the click recipe `recipe.json`
(`docs/browser-recipes.md`): invite, revoke invitation
and deactivate member passed (`done` after the read). The API addresses are
constants at the top of `connector.py`.

When the Slack plan has SCIM (Business+ and higher), the `scim` connector
with a token is the better choice: an official API instead of a browser session.

## How to connect

1. An app in Open Revoke with the `browser` integration, connection `slack`,
   field `workspace`: the subdomain, e.g. `acme` for `acme.slack.com` (a
   pasted address also works).
2. Page `/browser`, the "Log in" button next to Slack. It opens
   `https://<workspace>.slack.com/` in the browser. Sign in with a
   **Workspace Admin or Owner** account (the member list works for any
   account, invites and deactivation only for an admin).
3. "Check" in the connection settings, then "Sync now".

The session lives in the `browser-profile` volume. Signing out or an expired
session ends the sync with the state `needs_login`, and the accounts stay unchanged.

## How it works

- The Slack web client runs on `https://app.slack.com/client` and keeps the
  token of each workspace (`xoxc-...`) in `localStorage` under the key
  `localConfig_v2` (`teams.<team_id>.token`, `domain`, `url`). The connector
  reads it from an app.slack.com tab.
- The `d` cookie (domain `.slack.com`) goes along with every `fetch()`
  with `credentials: "include"`. The token does not work without the cookie.
- Every call: `POST https://<workspace>.slack.com/api/<method>`,
  body `application/x-www-form-urlencoded` with `token` and the parameters,
  run in a tab on the workspace origin
  (`https://<workspace>.slack.com/robots.txt`), that is, same-origin.
  From an app.slack.com tab the browser blocks the response: the API answers
  with `Access-Control-Allow-Origin: *`, and this excludes the `d` cookie
  ("Failed to fetch", checked 25.11.2026). The Slack web client itself
  sends `multipart/form-data` with parameters such as `_x_id`;
  a urlencoded form also works.

| Operation | Call (not verified) |
|---|---|
| `check` | `auth.test` |
| `list_accounts` | `users.list` with `limit=200`, next pages through `cursor` from `response_metadata.next_cursor` |
| `create_account` | recipe: `/admin`, "Invite People", e-mail, Enter, "Send", then `/admin/invites` must show the e-mail; the account from `users.lookupByEmail` |
| `delete_account` | recipe: `/admin`, filter by e-mail, the row `[data-qa-id=<ID>]` must contain the e-mail, row menu, `ws-members-action_deactivate`, "Deactivate" (`primary_action`) |

The recipe searches first by Slack's `data-qa` attributes (they do not
depend on the language), then by button names. The same menu item
(`ws-members-action_deactivate`) is "Deactivate account" for a member and
"Revoke invitation" for an invite. The confirmation dialog does not show the
e-mail, so the `check-row` step checks the identity: the row with the
member ID must contain the member's e-mail.

An invited member who has not signed in yet has an ID (`U...`) and is in
`users.list` with `is_invited_user`, so the verification of an invite works
at once.

## Mapping

- Skipped: `USLACKBOT`, `is_bot`, `is_app_user` (bots and apps) and
  members erased by Slack (`deleted`, name `deactivateduserNNN`,
  e-mail on `slack-corp.com`). The admin panel does not count them
  (checked 25.11.2026).
- `external_id` = `id` (`U...`), `email` = `profile.email` (lowercase),
  `display_name` = `profile.real_name`, `username` = `name`.
- Role: `primary_owner`, `owner`, `admin`, `single_channel_guest`
  (`is_ultra_restricted`), `guest` (`is_restricted`), `member`. For
  deactivated members `users.list` returns no role flags, so the role is empty.
- Status: `deleted: true` (deactivated) gives `suspended` (does not count
  toward the seat cost), `is_invited_user: true` gives `invited`, the rest `active`.
- `raw`: only flags and identifiers, no phone numbers and no photos.

A response `ok: false` with `invalid_auth`, `not_authed`, `token_revoked`,
`token_expired` or `account_inactive` is `needs_login`. Other errors
(e.g. `not_allowed_token_type`, `no_permission`) end the sync with an error.
HTTP 429 is retried up to 3 times after `Retry-After` (max. 60 s).

## Limits

- Pending invites are not read (we do not know if `users.list` returns
  them; not verified). An invite without an account in `users.list`
  shows up only after it is accepted.
- Guest invites (they need channels) are not supported.
- After `delete_account` the account stays in the list as `suspended`; it
  does not disappear. Read-back verification must take this into account.
- Enterprise Grid (several workspaces in an organization) is not checked; the
  connector reads one workspace.
- Limits of `users.list`: about 20 requests per minute (not verified).

## How to verify

1. Sign in to the workspace in noVNC (step 2 of "How to connect").
2. Record the panel traffic:
   ```bash
   docker compose exec app python -m app.devtools.capture --host slack.com --subdomains --out captures/slack.jsonl
   ```
   In noVNC open `https://app.slack.com/manage/<team_id>/people` (the
   member list in the admin panel), scroll the list to the end, invite a
   test address (a separate e-mail, not an employee), deactivate it. Ctrl+C.
3. Check in `captures/slack.jsonl`: the method names (`users.list`,
   `users.admin.invite`, `users.admin.setInactive` or their successors,
   e.g. `admin.users.*`), the form parameters, the shape of `members` and the pagination.
4. Check that `localStorage.localConfig_v2` on app.slack.com still has
   `teams.<id>.token` and `domain`: "Check" in the connection settings says
   "not logged in to the Slack workspace" when the key or the field is missing.
5. Fix the constants in `connector.py` and the parser in `mapping.py`, add a
   fixture (fictional data, `example.com`) and a test. Change "not verified"
   to the date of the check. Delete `captures/slack.jsonl`.

## Billing

`read_billing` (`Capability.READ_BILLING`) calls `retail.getAvailablePlans`,
the same as the `/admin/billing` page (an undocumented method). The current
product is `team_current_product` (e.g. `std_m_eur_v2`); its entry in `plans`
has `cost.unit_price` (cents per paid member per period),
`billable_active_users`, `total_recurring`; `payments_status.provisions_status.term_info.end_dt`
is the renewal date. Tiers: `std` = Pro, `plus` = Business+. Checked
25.11.2026 on the Pro plan: the price per member, the number of paid members,
the total and the renewal date match the billing page.

## Inactive members and the invoice

- Slack does not count accounts that the admin panel marks as "Inactive"
  (Billing Status column) on the invoice. `users.list` does not return
  this status, so the app cost is the price from billing times the active
  accounts, and it can be higher than the invoice until such an account is
  deactivated.
