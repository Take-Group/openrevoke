# open-revoke/backend/app/api/

FastAPI routers of the panel API: thin handlers that validate input with `app/schemas/`, call one `app/services/` module and return a schema. No business logic here. `router.py` mounts everything under `/api`; paths below are relative to `/api` unless noted.

- `__init__.py`: empty.
- `router.py`: builds `api_router`. `domain_router` (prefix `/api`, every route needs `require_admin`) includes the panel routers; `self_router` (`/api/me`, any signed-in user, cookie or token); `session_router` (`/api/api-tokens`, the panel cookie only); `health`, `auth`, public currencies and app catalog, the Google OAuth callback and `browser_live` sit outside it; `dev_router` is the fake panel.
- `deps.py`: `SessionDep` (AsyncSession), `DispatcherDep`, `ActionDispatcherDep`, `ScanDispatcherDep` (Temporal starters from `app/temporal/`).
- `auth_deps.py`: `get_current_session` (cookie only), `get_current_user` (API token `Authorization: Bearer`, else the cookie; a read token gets only safe methods), `require_admin`, `require_client_header` (CSRF header `X-Open-Revoke-Client` on unsafe methods with the cookie), `bearer_token`; aliases `CurrentUserDep`, `CurrentSessionDep`, `AdminDep`, `OptionalSessionDep`. Use `AdminDep` for admin-only routes.
- `params.py`: shared list query params `SearchQuery`, `Limit`, `Offset`, `DEFAULT_LIMIT`.
- `errors.py`: `register_error_handlers` maps `app.services.errors` exceptions to HTTP codes (`{"detail": ...}`); `ERROR_RESPONSES`, `UNAVAILABLE_RESPONSE`, `RATE_LIMITED_RESPONSE` for OpenAPI.
- `host_check.py`: `AllowedHostsMiddleware` refuses unknown `Host`/`X-Forwarded-Host` (DNS rebinding); `host_name`.
- `health.py`: GET `/health` (with `version`), GET `/health/ready` (public, no `/api` prefix of domain_router).
- `auth.py`: prefix `/api/auth`, public. GET `/state`, POST `/setup` (needs the setup token), `/setup/check`, `/login`, `/totp`, `/totp/skip`, `/register`, `/signup`, `/2fa/setup`, `/2fa/enable`, `/2fa/disable`, `/password/reset`, `/password/change`, `/logout`, GET `/invites/{token}`. Services: `services.auth.sign_in`, `passwords_flow`, `sessions`. Sets the session cookie.
- `users.py`: admins only. GET/PATCH/DELETE `/users`, POST `/users/{id}/approve`, `/reset-link` and `/reset-totp`, GET/POST/DELETE `/invites`, GET/PATCH `/organization` (with sign-up rules). Services: `services.auth.users`, `invites`, `services.organization`.
- `api_tokens.py`: GET/POST `/api-tokens`, DELETE `/api-tokens/{id}`: the signed-in user's API tokens and the MCP URL; cookie only (`services.auth.api_tokens`).
- `me.py`: GET `/me/access`, POST `/me/access-requests`: the signed-in user's own accounts and requests; the only API a `user` reaches. Service `my_access`.
- `dashboard.py`: GET `/dashboard` (`services.dashboard.get_dashboard`).
- `setup_checklist.py`: GET `/onboarding`, PUT `/onboarding/choices`, POST `/onboarding/dismiss` (`services.setup_checklist`).
- `people.py`: `/people` list/create, POST `/people/import`, GET/PATCH/DELETE `/people/{id}`, POST `/people/{id}/offboard` and `/onboard`. Services: `people`, `people_import`, `offboarding`, `onboarding`.
- `apps.py`: `/apps` CRUD, GET/POST `/apps/{id}/accounts`. Services: `apps`, `accounts`; delete also drops the sync schedule (`sync_dispatch`).
- `accounts.py`: PATCH `/accounts/{id}` (`services.accounts`).
- `connections.py`: GET `/connectors`, PUT `/apps/{id}/connection`, POST `/apps/{id}/connection/check` and `/sync` (202, `sync_requests.request_sync`), GET `/apps/{id}/sync-runs`. Services: `connections`, `sync_dispatch`.
- `actions.py`: POST/GET `/actions`, POST `/actions/batch/{batch_id}/approve`, `/actions/{id}/approve`, `/cancel`, `/complete`, `/retry`, `/by-hand`, `/reveal-secret`, GET `/actions/{id}/screenshot` (PNG). Services: `actions`, `action_approval` (starts the workflow), `action_retry`, `action_queries`.
- `recipe_fixes.py`: GET `/recipe-fixes` (`?recipe_app=`), POST `/recipe-fixes/{id}/approve` and `/reject`. Service `recipe_fixes`.
- `discovery.py`: GET `/discovery`, POST `/discovery/source`, `/discovery/scan` (202), GET `/discovery/scans`, `/discovery/apps`, GET/PATCH `/discovery/apps/{id}`, POST `/discovery/apps/{id}/track`, GET `/people/{id}/discovered-apps`. Services: `discovery`, `discovery_review`, `discovery_setup`, `scan_requests`.
- `google_oauth.py`: POST `/discovery/google-oauth/start` (admin); `callback_router` GET `/api/discovery/google-oauth/callback` (public, 303 redirect to the panel). Service `google_oauth`.
- `google_cloud_setup.py`: GET/POST `/discovery/google-cloud-setup` (`services.google_cloud_setup.service`, browser automation).
- `browser.py`: GET `/browser`, POST `/browser/open` (`services.browser`); `public_router` GET `/api/browser/policy` (no sign-in: the browser container polls which password manager to force-install).
- `browser_live.py`: `/api/browser/live/{path}` (noVNC files) and WebSocket `/websockify`; admin only, reads the cookie itself, checks same origin.
- `audit.py`: GET `/audit` (`services.audit`).
- `ai.py`: GET/PUT `/ai-settings`, POST `/ai-settings/models` and `/test` (`services.ai_settings`).
- `slack_agent.py`: GET/PATCH/DELETE `/slack-agent`, POST `/slack-agent/app`, `/avatar`, PUT `/slack-agent/tokens`, GET `/slack-agent/oauth/start` and `/oauth/callback` (back to `/settings/slack`). Service `slack_agent_setup`.
- `access_requests.py`: GET `/access-requests` (`services.access_requests`).
- `catalog.py`: `public_router` (public) GET `/api/catalog/apps`, GET `/api/catalog/logos/{slug}.png` (`app.catalog.lookup`).
- `currencies.py`: `public_router` GET `/api/currencies` (public); `router` POST `/exchange-rates/refresh` (admin). Service `exchange_rates`.
- `system.py`: GET `/system/version` (admin): running version and the newest release (`services.system_info`).
- `dev_panel.py`: fake SaaS admin panel at `/api/dev/fake-panel` (login, users, invite, remove, HTML `/admin` for the click recipe, `/ui?version=2` to break its look), no panel session; 404 unless `fake_connector_enabled()`. Backs `connectors/browser_fake`.
