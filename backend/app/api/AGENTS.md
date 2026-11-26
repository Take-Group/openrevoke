# open-revoke/backend/app/api/

FastAPI routers: thin handlers that validate with `app/schemas/`, call one `app/services/` module and return a schema; no business logic. `router.py` mounts all under `/api`; paths below are relative to `/api` unless noted.

- `__init__.py`: empty.
- `router.py`: `api_router`. `domain_router` (`/api`, every route `require_admin`) holds the panel routers; `self_router` (`/api/me`, app logo GET: any signed-in user, cookie or token); `session_router` (`/api/api-tokens`, cookie only); outside them: `health`, `auth`, public currencies and catalog, Google OAuth callback, `browser_live`, `dev_router` (fake panel).
- `deps.py`: `SessionDep`, `DispatcherDep`, `ActionDispatcherDep`, `ScanDispatcherDep` (Temporal starters from `app/temporal/`).
- `auth_deps.py`: `get_current_session` (cookie only), `get_current_user` (`Authorization: Bearer` API token, else cookie; a read token gets only safe methods), `require_admin`, `require_client_header` (CSRF header `X-Open-Revoke-Client` on unsafe cookie requests), `bearer_token`; aliases `CurrentUserDep`, `CurrentSessionDep`, `AdminDep` (use for admin-only routes), `OptionalSessionDep`.
- `params.py`: list params `SearchQuery`, `Limit`, `Offset`, `DEFAULT_LIMIT`.
- `errors.py`: `register_error_handlers` maps `app.services.errors` to HTTP codes (`{"detail": ...}`); `ERROR_RESPONSES`, `UNAVAILABLE_RESPONSE`, `RATE_LIMITED_RESPONSE` for OpenAPI.
- `host_check.py`: `AllowedHostsMiddleware` refuses unknown `Host`/`X-Forwarded-Host` (DNS rebinding); `host_name`.
- `health.py`: `/health` (with `version`), `/health/ready`; public, outside `/api`.
- `auth.py`: `/api/auth`, public: GET `/state`, POST `/setup` (setup token; then `services.telemetry.report` in the background), `/setup/check`, `/login`, `/totp`, `/totp/skip`, `/register`, `/signup`, `/2fa/setup|enable|disable`, `/password/reset|change`, `/logout`, GET `/invites/{token}`. Sets the session cookie; services `auth.sign_in`, `passwords_flow`, `sessions`.
- `users.py`: `/users` GET/PATCH/DELETE, POST `/users/{id}/approve|reset-link|reset-totp`, `/invites` GET/POST/DELETE, `/organization` GET/PATCH (sign-up rules). Services `auth.users`, `invites`, `organization`.
- `api_tokens.py`: `/api-tokens` GET/POST, DELETE `/{id}`: own API tokens and the MCP URL, cookie only (`auth.api_tokens`).
- `me.py`: the only API a `user` reaches: GET `/me/access`, POST `/me/access-requests`, GET `/me/team`, `/me/approvals`, `/me/approvals/{id}`, POST `.../approve|reject`. Services `access.my_access`, `access.my_approvals`.
- `dashboard.py`: GET `/dashboard` (`dashboard.get_dashboard`).
- `setup_checklist.py`: GET `/onboarding`, PUT `/onboarding/choices`, POST `/onboarding/dismiss`.
- `people.py`: `/people` list/create, POST `/people/import`, `/people/{id}` GET/PATCH/DELETE, POST `/offboard`, `/onboard`. Services `people`, `people_import`, `offboarding`, `onboarding`.
- `apps.py`: `/apps` CRUD (filter `category`), POST `/apps/bulk`, `/apps/{id}/accounts` GET/POST, POST `/accounts/bulk` (pasted e-mails, `?dry_run`), PUT/DELETE `/apps/{id}/logo`; `logo_router` GET logo for any signed-in user (`nosniff`, CSP, ETag). Delete drops the sync schedule (`sync_dispatch`).
- `accounts.py`: POST `/accounts/import` (CSV, `?dry_run`, `?create_apps`), PATCH `/accounts/{id}`.
- `connections.py`: GET `/connectors`, PUT `/apps/{id}/connection`, POST `.../check`, `.../sync` (202, `sync_requests.request_sync`), GET `/apps/{id}/sync-runs`.
- `actions.py`: POST/GET `/actions`, POST `/actions/batch/{batch_id}/approve`, `/actions/{id}/approve|cancel|complete|retry|by-hand|reveal-secret`, GET `/screenshot` (PNG). Services `actions`, `action_approval` (starts the workflow), `action_retry`, `action_queries`.
- `recipe_fixes.py`: GET `/recipe-fixes` (`?recipe_app=`), POST `/{id}/approve|reject`.
- `discovery.py`: GET `/discovery`, POST `/discovery/source`, `/scan` (202), GET `/scans`, `/apps`, `/apps/{id}` GET/PATCH, POST `/apps/{id}/track`, GET `/people/{id}/discovered-apps`. Services `discovery`, `discovery_review`, `discovery_setup`, `scan_requests`.
- `google_oauth.py`: POST `/discovery/google-oauth/start` (admin); `callback_router` GET `/api/discovery/google-oauth/callback` (public, 303 to the panel).
- `google_cloud_setup.py`: GET/POST `/discovery/google-cloud-setup` (browser automation).
- `browser.py`: GET `/browser`, POST `/browser/open`; `public_router` GET `/api/browser/policy` (no sign-in: the browser container polls which password manager to install).
- `browser_live.py`: `/api/browser/live/{path}` (noVNC) and WebSocket `/websockify`; admin only, reads the cookie itself, checks same origin.
- `audit.py`: GET `/audit`, `/audit/export` (`csv`, `jsonl`).
- `client_ip.py`: `client_ip(request)`.
- `ai.py`: GET/PUT `/ai-settings`, POST `/models`, `/test`.
- `slack_agent.py`: `/slack-agent` GET/PATCH/DELETE, POST `/app`, `/avatar`, PUT `/tokens`, GET `/oauth/start|callback` (back to `/settings/slack`). Service `slack_agent_setup`.
- `access_requests.py`: GET `/access-requests` (filters), `/export` (CSV), `/{id}`, POST `/{id}/approve|reject` (admin step or override). Services `access.queries`, `access.flow`.
- `access_profiles.py`: `/access-profiles` GET/POST, GET `/app-roles`, `/{id}` GET/PATCH/DELETE, `/{id}/members` GET/POST, `/people/{id}/access-profiles` GET/POST, DELETE `.../{profile_id}`, GET `/people/{id}/access-drift`. Services `access.profiles`, `profile_assignment`, `profile_members`.
- `catalog.py`: `public_router` GET `/api/catalog/apps`, `/api/catalog/logos/{slug}.png`; `router` (admin) GET `/catalog/search` (`catalog_search`: `connector_key`, `already_added`, `discovered_users`).
- `currencies.py`: public GET `/api/currencies`; admin POST `/exchange-rates/refresh`.
- `system.py`: GET `/system/version` (admin): running and newest version (`system_info`).
- `dev_panel.py`: fake SaaS admin panel at `/api/dev/fake-panel` (login, users, invite, remove, HTML `/admin` for the click recipe, `/ui?version=2` breaks its look), no session; 404 unless `fake_connector_enabled()`. Backs `connectors/browser_fake`.
