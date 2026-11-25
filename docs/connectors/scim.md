# SCIM 2.0 connector

Key: `scim`. Method: SCIM 2.0 (RFC 7643, RFC 7644), Open Revoke is the
client. Code: `backend/app/connectors/scim/`.

One connector for every app that exposes a SCIM `/Users` endpoint
with a Bearer token. It reads users, creates them, and deactivates or
deletes them.

## How to connect

1. In the app's admin panel, find the SCIM settings (often under "SSO",
   "Provisioning" or "User provisioning"). SCIM is often available only on
   Enterprise plans.
2. Copy the SCIM base address and generate a token. Store the token in a
   password manager.
3. In Open Revoke: an app with the `scim` integration, connection `scim`:
   - `base_url`: the address before `/Users`, e.g. `https://app.example.com/scim/v2`,
   - `token`: the secret,
   - `user_filter`: empty. A SCIM filter (e.g. `userName sw "a"`) narrows the
     list, and users outside the filter count as deleted,
   - `delete_mode`: `deactivate` (default, `active: false`) or `delete`,
   - `page_size`: 100; lower it when the server rejects larger pages.
4. "Check", then "Sync now".

Some apps allow only one active SCIM token or tie SCIM to an identity
provider (Okta, Entra). Generating a new token can then break the existing
integration. Check this before you connect.

## Endpoints

Headers: `Authorization: Bearer <token>`,
`Accept: application/scim+json, application/json`,
`Content-Type: application/scim+json`.

| Operation | Call |
|---|---|
| `check` | `GET {base}/Users?startIndex=1&count=1` |
| `list_accounts` | `GET {base}/Users?startIndex=N&count=page_size[&filter=…]`, until the number fetched reaches `totalResults` |
| `create_account` | `POST {base}/Users` with `schemas`, `userName` (= e-mail), `emails` (primary), `name`, `displayName`, `active: true` |
| `delete_account` | `deactivate`: `PATCH {base}/Users/{id}` with `PatchOp` `replace` `active` = `false`; `delete`: `DELETE {base}/Users/{id}` |

## Mapping

- `external_id` = `id` of the SCIM resource.
- `email`: the `emails` entry with `primary: true`, otherwise the first one,
  otherwise `userName` when it looks like an e-mail. Lowercase.
- `display_name`: `displayName`, otherwise `name.formatted`, otherwise the
  first and last name.
- Role: `roles` with `primary: true` or the first one. Most servers do not
  send it.
- Status: `active: false` gives `suspended`. A missing `active` field means
  an active account (the field is optional in SCIM).

## Full list or an error

- A response without `totalResults` is an error, because there is no way to
  check if the list is complete.
- An empty page before `totalResults` is reached gives `IncompleteListError`.
- A page with only `id` values already seen (the server ignores `startIndex`)
  also gives `IncompleteListError`, instead of a loop.
- More than 1000 pages is an error, not a truncated list.

## Limits

- Some servers do not accept a `PATCH` with `path: "active"` and require the
  form `{"op": "replace", "value": {"active": false}}`. We do not support
  this yet (not verified on specific apps).
- Servers with cursor pagination (the SCIM extension from 2024) are not
  supported, only `startIndex` and `count`.
- The connector does not read groups or roles from extensions (e.g. enterprise).
- The behaviour follows RFC 7644; it is not tested on any real SCIM server
  (status 22.11.2026).
