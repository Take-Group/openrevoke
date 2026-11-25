# Google Workspace connector

Key: `google_workspace`. Method: official API (Admin SDK Directory API).
Code: `backend/app/connectors/google_workspace/`.

The connector reads the users of the domain as app accounts and can be the
people source (`is_people_source`). It creates a user and **suspends** a
user, but never deletes one: a deletion erases mail and files for good.

## How to connect

Two paths, both on the `/discovery` page at the first connection:

- **Connect with Google (OAuth), the default since 23.11.2026.** The admin
  signs in with a Google account and approves the permissions. Reason: Google
  Cloud organizations created since 03.05.2024 have the policy
  `iam.managed.disableServiceAccountKeyCreation` on by default and cannot
  create a JSON key for a service account (Google documentation "Secure by
  default organizations", checked 23.11.2026).
- **Service account key** with domain-wide delegation (described below).

### Connect with Google (OAuth)

The simplest way: the "Automatic" tab on `/discovery`. The admin signs in to
Google in the shared browser, and Open Revoke creates the project, the
consent screen and the OAuth client by itself (`skills/backend/google-cloud-setup.md`).
Checked on a real Workspace 23.11.2026. Below is
the same path by hand ("Guided (links)").

Every installation has the company's own OAuth client. A shared Open Revoke
client does not work with self-hosting: Google sends the admin back to the
installation's address, and that address must be entered in the client.

1. console.cloud.google.com, with the company account: a project, enable the
   **Admin SDK API**.
2. Google Auth Platform: Branding (app name), Audience: **Internal**.
   Internal needs no verification by Google. External in Testing mode
   also works, but then Google issues a refresh token valid for 7 days
   (Google OAuth 2.0 documentation, "Refresh token expiration", checked
   23.11.2026).
3. Clients: a client of type **Web application**, the authorized redirect
   URI from the panel (`<GOOGLE_OAUTH_REDIRECT_BASE or PUBLIC_URL>/api/discovery/google-oauth/callback`).
4. In the panel: client ID and client secret, "Connect with Google", sign-in
   as a Workspace admin, consent.

Google accepts `http` only for `localhost`. Google rejects an address in a
domain outside the public suffix list (e.g. `http://panel.localhost`)
with the error `invalid_request` ("doesn't comply with Google's OAuth 2.0
policy", checked 23.11.2026). So the local stack also exposes the panel on
`http://localhost:18410` and sets `GOOGLE_OAUTH_REDIRECT_BASE` to this address.
A VPS needs a domain with HTTPS.

Flow: `POST /api/discovery/google-oauth/start` saves in Redis an
encrypted, one-time `state` (10 minutes) with the client, the PKCE verifier
and the panel admin's e-mail, and returns the address of the consent screen
(`access_type=offline`, `prompt=consent`). `GET /api/discovery/google-oauth/callback`
does not need a panel session (the redirect address can be a different host
than the panel): it exchanges the code for a refresh token, reads the
admin's e-mail from userinfo and calls the same `setup_google_source` as the
key path. The result goes back to the panel in
`/discovery?google=connected` or `?google_error=…`.

Scopes on the consent screen: `openid`, `email`, `admin.directory.user.readonly`,
`admin.directory.user` (suspension during offboarding),
`admin.reports.audit.readonly`, `admin.directory.user.security`. Reading the
directory and the audit log is required; without the other scopes only the
writes or the token inventory are off. Every call checks if Google granted
its scope.

API calls run with the permissions of the admin who signed in. When that
admin loses the admin role, is deleted or revokes access, Google returns
`invalid_grant` and the connection goes to `needs_login`. A button in the
panel to reconnect does not exist yet (23.11.2026): you have to delete the
Google Workspace app and connect again.

### Service account key

You need: a Google Cloud service account with domain-wide delegation
and the e-mail of the super admin on whose behalf the service
account acts.

1. Google Cloud Console: create a project (or use an existing one) and enable
   the **Admin SDK API**.
2. IAM & Admin, Service Accounts: create a service account. No roles in the
   project, they are not needed.
3. In the service account, the Keys tab: Add key, JSON. The file is a secret.
   Paste its content into the "Service account key (JSON)" field in Open
   Revoke and delete the file from the disk. Keep the key in a password
   manager, never in a repository.
4. Note the "Unique ID" (Client ID) of the service account.
5. admin.google.com, Security, Access and data control, API controls,
   Manage Domain Wide Delegation: add the Client ID with the scopes:
   - `https://www.googleapis.com/auth/admin.directory.user.readonly`:
     read (sync, people source, connection check),
   - `https://www.googleapis.com/auth/admin.directory.user`: write
     (create and suspend). Without this scope, reads work.
6. In Open Revoke: an app with the `api` integration, connection `google_workspace`:
   - `admin_email`: the super admin (or an admin with a role to manage
     users) on whose behalf the service account acts,
   - `customer`: leave `my_customer`,
   - `domain`: empty, unless you want to read only one of several domains.
7. "Check", then "Sync now".

Delegation changes in the Google panel usually take effect after a few
minutes, sometimes longer (not verified, depends on Google).

## How authentication works

`auth.access_token(ctx, scope)` picks the path: the service account key when
it is set, otherwise the OAuth refresh token (`oauth.py`, the access token
stays in process memory until one minute before it expires). The key path:

The connector signs a JWT with the private key of the service account
(library `google-auth`, `google.auth.crypt` and `google.auth.jwt`) with the
fields `iss` (the service account's e-mail), `sub` (the admin), `scope`,
`aud` (the token address from the key file, by default
`https://oauth2.googleapis.com/token`). It exchanges the JWT for an access
token with a `POST` to `token_uri` with
`grant_type=urn:ietf:params:oauth:grant-type:jwt-bearer`. A read asks only
for the `readonly` scope, a write for the full `admin.directory.user`.

A refusal by Google (`invalid_grant`, `unauthorized_client`, `invalid_client`,
`access_denied`, HTTP 401) gives `needs_login`: the accounts stay unchanged,
and the dashboard shows an alert about rejected credentials.

## Endpoints

| Operation | Call |
|---|---|
| `check` | `GET https://admin.googleapis.com/admin/directory/v1/users?customer=my_customer&maxResults=1` |
| `list_accounts`, `list_people` | `GET .../users?customer=…` or `?domain=…`, `maxResults=500`, `projection=basic`, `viewType=admin_view`, next pages through `pageToken` until there is no `nextPageToken` |
| `create_account` | `POST .../users` with `primaryEmail`, `name.givenName`, `name.familyName`, `password` (random 24 characters), `changePasswordAtNextLogin: true` |
| `delete_account` | `PUT .../users/{id}` with `{"suspended": true}` (users.update, suspension) |

## Mapping

- Account: `external_id` = `id` of the Google user, `email` = `primaryEmail`
  (lowercase), `display_name` = `name.fullName`, role `super_admin`
  (`isAdmin`), `delegated_admin` (`isDelegatedAdmin`) or `user`.
- Status: `suspended` or `archived` gives `suspended`, the rest `active`.
- Person: aliases from `aliases`, `nonEditableAliases` and `emails[].address`
  without the primary e-mail. The employee ID comes from `externalIds` with
  the type `organization` (the "Employee ID" field in the admin console).
  `active` = not suspended and not archived.
- `raw` keeps only selected fields (id, e-mail, admin flags, suspension,
  organizational unit, dates, 2SV). Phone numbers, addresses and recovery
  e-mails do not go into the database.

## App scan (discovery, since 23.11.2026)

The connector has `Capability.DISCOVER_APPS`: it reads which third-party
apps people sign in to with their Google account ("Sign in with Google",
OAuth consents). Read only. Description of the whole feature: `skills/backend/app-discovery.md`.

Delegation scopes (besides `admin.directory.user.readonly`):

- `https://www.googleapis.com/auth/admin.reports.audit.readonly`: required.
  Reports API, the events `token` / `authorize` (who gave an app access
  and when) and `admin` / `DELETE_USER` (who was deleted from the directory).
- `https://www.googleapis.com/auth/admin.directory.user.security`:
  optional. `tokens.list` of each person: the tokens the person has now, also
  for apps authorized before the log window. This scope also allows deleting
  tokens; the connector only reads. Without it the scan works, and the panel
  shows "Unknown" in the token column.

The `/discovery` page does the first connection (`POST /api/discovery/source`):
it checks the directory read and the audit scope token before it saves
anything.

| Operation | Call |
|---|---|
| sign-ins and consents | `GET https://admin.googleapis.com/admin/reports/v1/activity/users/all/applications/token?eventName=authorize&startTime=…&endTime=…&maxResults=1000`, pages through `pageToken` |
| deleted users | `GET …/applications/admin?eventName=DELETE_USER&startTime=…&endTime=…` |
| tokens of a person | `GET https://admin.googleapis.com/admin/directory/v1/users/{email}/tokens`, 8 at a time; 404 (person deleted in the meantime) skips the person |

Limits:

- Google keeps the log for at most 180 days (`activities.list` documentation,
  checked 23.11.2026). Someone who left earlier and had the account deleted
  left no trace. So the scan saves its result and runs every 24 h: the
  history grows from the day of the connection.
- The documentation does not say if every "Sign in with Google" creates an
  `authorize` event, or only the first consent (not verified). "Last sign-in"
  can therefore be the date of the last consent, not of the last sign-in.
- Sign-in with e-mail and password leaves no trace in Google. The scan does
  not see such apps.
- Google apps and devices (Chrome, Android, iOS, "Google …") are
  skipped by the `GOOGLE_OWNED_NAMES` list. The list is not complete.
- Several OAuth clients of one app are merged by name. Two different
  apps with the same name merge into one (not seen in the test
  data).
- The `id.time` fields in the response: the documentation says "epoch
  seconds", the examples return RFC 3339. The parser accepts both.

## Limits

- Creating an account needs a first and last name. The temporary password
  comes back in `CreatedAccount.temporary_password`. It must be shown to the
  admin once and never saved in the database or in a log.
- Google service accounts and groups are not listed, only users.
- The domain's password policy can reject the generated password (not checked).
- The connector does not delete a user. A person deletes the user in the
  Google panel.
- Paths and fields are checked against knowledge of Directory API v1, not on
  a real domain (status 22.11.2026). Connect with Google is checked locally
  up to the Google consent screen (a made-up client), without a real OAuth
  client (23.11.2026). Still to be checked on a real domain.
