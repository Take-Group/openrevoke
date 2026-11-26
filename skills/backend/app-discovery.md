# Skill: App discovery (Google Workspace scan)

## What it does

The scan reads from Google Workspace which third-party apps people
sign in to with the company account ("Sign in with Google", OAuth consents). The panel
shows the list of apps, who signed in and which of those people left the company, are
suspended or deleted in Google. Read only. A sign-in is proof that the app
is used, not proof of a paid seat: only the app's connector confirms an account
in the app.

First run: an admin who chose Google Workspace on `/welcome`
sees the step "Connect Google Workspace" on the dashboard
(`skills/backend/setup-checklist.md`). The `/discovery` page guides through connecting Google Workspace in two ways:
"Connect with Google" (OAuth, the company's OAuth client, the default) or a service
account key. Both create a Google Workspace app with a connection (people
source), start a sync and the first scan. OAuth details:
`docs/connectors/google_workspace.md`, section "Connect with Google".

## Where the data comes from (Google)

| Read | API | Scope | Required |
|---|---|---|---|
| users and their state | Directory `users.list` | `admin.directory.user.readonly` | yes |
| consents and sign-ins, max 180 days | Reports `activities.list`, `token`, `authorize` | `admin.reports.audit.readonly` | yes |
| deleted users | Reports, `admin`, `DELETE_USER` | the same | yes |
| current tokens of each person | Directory `tokens.list` | `admin.directory.user.security` | no |

Without the tokens scope the scan works, `token_active` is `null`, and the scan stores
a note. The tokens scope also allows revoking them; Open Revoke only reads.
Details: `docs/connectors/google_workspace.md`, section "App scan".

## Files

| File | What it does |
|---|---|
| `backend/app/connectors/discovery.py` | `AppDiscovery` (connector mixin), `AppGrant`, `DirectoryUser`, `DiscoveryResult` |
| `backend/app/connectors/base.py` | `Capability.DISCOVER_APPS` |
| `backend/app/connectors/google_workspace/discovery.py` | requests: Reports API, `tokens.list`, tokens for scopes |
| `backend/app/connectors/google_workspace/discovery_mapping.py` | pure parsing, `GrantBook` (merges events and tokens), skipped Google apps |
| `backend/app/connectors/google_workspace/connector.py` | `discover_apps` |
| `backend/app/connectors/fake/discovery.py` | fixed scan data for the `fake` connector |
| `backend/app/models/scan_run.py`, `discovered_app.py`, `discovered_grant.py` | tables `scan_run`, `discovered_app`, `discovered_grant` |
| `backend/app/services/discovery_scan.py` | scan run: `start_run`, `run`, `fail_run`, time window, scan lock |
| `backend/app/services/discovery_apply.py` | saving the result: grouping by app name, state in the directory (`Directory.classify`) |
| `backend/app/services/discovery.py` | reads: overview, list with risk, details, a person's apps, `apps_at_risk` |
| `backend/app/services/discovery_review.py` | "Track" (a `manual` app or an existing one with the same name or catalog key; sets `app.catalog_key`; `create_accounts`), "Ignore" |
| `backend/app/services/discovery_setup.py` | first Google connection: scope check, app, connection, sync, scan |
| `backend/app/services/google_oauth.py`, `backend/app/api/google_oauth.py` | Connect with Google: `state` in Redis, callback without a panel session, then `setup_google_source` |
| `backend/app/connectors/google_workspace/oauth.py`, `auth.py`, `scopes.py` | consent screen, code exchange (PKCE), refresh token; `access_token` picks the key or OAuth |
| `backend/app/services/discovery_sources.py` | which connections can scan |
| `backend/app/services/scan_requests.py`, `scan_dispatch.py` | "Scan now", `ScanDispatcher` interface |
| `backend/app/temporal/scan_*.py` | `ScanConnectionWorkflow`, activities, schedule `scan-connection-<id>`, dispatcher |
| `backend/app/api/discovery.py` | endpoints `/api/discovery...`, `/api/people/{id}/discovered-apps` |
| `backend/app/services/dashboard.py` | alert `discovered_sign_ins_at_risk` |
| `frontend/src/components/discovery/` | page, wizard (`discovery-setup.tsx`: `google-oauth-setup.tsx` or `service-account-setup.tsx`), table, details, review buttons |
| `frontend/src/hooks/use-discovery.ts`, `frontend/src/lib/api/discovery-types.ts` | hooks and types |

## Flow

1. `POST /api/discovery/scan` (or the schedule every `SCAN_INTERVAL_HOURS`,
   default 24 h) creates a `scan_run` and starts `ScanConnectionWorkflow`.
2. `discovery_scan.run` takes the scan lock (`open-revoke:scan-lock:<id>`),
   separate from the connection lock: a scan takes minutes, and a sync gives up
   at once when its lock is taken.
3. Window: the first scan covers `SCAN_LOOKBACK_DAYS` (180, the Google limit), later ones start at the
   end of the last successful scan minus `SCAN_OVERLAP_HOURS` (72), because Google
   adds events with a delay. The end of the window is now minus 2 min.
4. The connector returns `DiscoveryResult`. Write in one transaction:
   - app = normalized name (`app_key`), several OAuth client ids
     of one app (web, desktop) are one row,
   - `discovered_grant` per pair (app, e-mail); dates only
     widen, so reading the same window again breaks nothing,
   - every entry gets a state in the directory: `active`, `suspended`, `deleted`
     (in `DELETE_USER`, or an address in the company domain that is not in the directory),
     `external`; `token_active` only when tokens were read.
5. A connector error ends the scan as `failed`. The scan does not change the connection status.

Risk is computed on read (`grant_risk`): `deleted`, `suspended`, or
a person in Open Revoke with the status `left`. The person is matched by primary
e-mail and aliases on read, so a person added after the scan matches
at once.

## Track with accounts

`POST /api/discovery/apps/{id}/track` with `{"create_accounts": true}` also
adds a manual account (`status=active`, `kind=person`, matched by e-mail) for
every grant with `directory_status = active`, through
`services/accounts_import.add_people_accounts`. Existing accounts stay. Only
for apps without a connector (`integration = manual`); a connected app gets
its accounts from the sync, and the count is 0. Off by default: a Google
sign-in proves use, not a paid seat. The answer carries `accounts_created`;
the audit gets `discovery.accounts_created` (count) and `accounts.imported`
(`via: discovery`). Panel: the switch "Also add accounts for the N people who
signed in" next to Track on `/discovery/[id]` (N = active sign-ins).

Untracked discovered apps that the catalog knows also lead the grid of
"Add several apps" (`services/catalog_search.discovered_untracked`).

## How to extend

- Microsoft Entra: a new connector inherits `AppDiscovery`, sets
  `discovery_scopes` and adds `Capability.DISCOVER_APPS`. The rest (write,
  workflow, panel) works without changes. The panel wizard knows only Google today
  (`discovery_setup.py`, `discovery-setup.tsx`).
- Name, website and logo of known apps: the `backend/app/catalog/` folder (skill `app-catalog.md`). A new app is an entry in `apps.json` and a logo from the script.
- List of skipped Google apps: `GOOGLE_OWNED_NAMES` in
  `discovery_mapping.py`. The admin hides the rest with the "Ignore" button.
- New result field: `AppGrant` or `DiscoveryResult`, write in
  `discovery_apply.py`. Check by hand: a `fake` connection, "Scan now"
  on `/discovery`, the result in the panel or `dc exec postgres psql -U postgres -d open_revoke -c "select * from discovered_grant"`.
