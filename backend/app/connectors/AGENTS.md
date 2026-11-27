# open-revoke/backend/app/connectors/

One folder per SaaS app. A connector only talks to the app and returns data (`RemoteAccount`, `RemotePerson`, `DiscoveryResult`); it never writes to the database (`services/sync.py` stores). Parsing lives in pure functions in `<key>/mapping.py`. A new connector is one line in `registry.py`.

`Connector` (in `base.py`): class attributes `key`, `display_name`, `integration`, `auth_kind`, `capabilities`, `config_schema`, `login_url`, `admin_url`, `delete_suspends`, `target_fields`. Methods: `check(ctx)`, `list_accounts(ctx)` (abstract, must be complete or raise `IncompleteListError`), `create_account(ctx, req)`, `delete_account(ctx, account)`, `list_people(ctx)` (optional, per `capabilities`), `login_page`, `browser_origins`. Missing session or 401 raises `NeedsLogin`.

Support by connector (L = list_accounts, C = create, D = delete, P = list_people, S = discover_apps, B = read_billing):
google_workspace (API, service account or OAuth): L C D(suspends) P S. fake (API): L C D P S. github (API token), scim (SCIM token): L C D. slack (browser session): L C D B. claude, chatgpt, browser_fake (browser session, `fetch()` in a panel tab): L C D.

- `__init__.py`: empty.
- `base.py`: `Connector`, `ConnectorContext` (`config`, `secrets`, `http`, `browser`), `Capability`, `AuthKind`, `RemoteAccount`, `RemotePerson`, `BillingInfo` (`read_billing`), `CreateAccountRequest`, `CreatedAccount`, `CheckResult`, `SecretField` (secret config field the API never returns), `secret_field_names`.
- `errors.py`: `ConnectorError`, `NeedsLogin`, `IncompleteListError` (own module, so `browser_api.py` and `recipes/` need not import `base.py`).
- `registry.py`: `all_connectors()`, `get_connector(key)`, `UnknownConnectorError`; `fake` and `browser_fake` only when `fake_connector_enabled()` (DEBUG or `OPEN_REVOKE_ENABLE_FAKE_CONNECTOR`).
- `http.py`: `build_http_client` (timeout, user agent, no redirects), `raise_for_app_error`, `json_body`, `check_page_limit` (`MAX_PAGES`); used by API connectors.
- `browser_api.py`: `BrowserSession` protocol (`open`, `fetch`, `run_recipe`, `captured_header`, `cookies`, `local_storage`, `evaluate`), `BrowserResponse`, `BrowserUnavailableError`, `raise_for_browser_error`, `browser_json`; real implementation is `app/browser/session.py`.
- `discovery.py`: `AppDiscovery` mixin (`discover_apps(ctx, since, until)`, `discovery_scopes`), `AppGrant`, `DirectoryUser`, `DiscoveryResult`; stored by `services/discovery_scan.py`.
- `fake/`: own AGENTS.md. deterministic API connector for development.
- `google_workspace/`: own AGENTS.md. Directory API, OAuth and service account, app discovery.
- `github/`, no map: `connector.py` (`GitHubConnector`: org members and pending invitations, token config), `mapping.py` (`member_to_account`, `invitation_to_account`, Link-header paging).
- `scim/`, no map: `connector.py` (`ScimConnector`: generic SCIM 2.0 `/Users`, delete = deactivate PATCH), `mapping.py` (`parse_list_response`, `user_to_account`, `create_user_body`).
- `slack/`, no map: `connector.py` (`SlackConnector`: browser session, `xoxc` token from local storage plus `d` cookie, API calls from a tab on the workspace origin; writes with the click recipe), `recipe.json` (invite, deactivate on the admin page), `mapping.py` (`member_to_account`, `token_from_local_config`, `next_cursor`).
- `claude/`, no map: `connector.py` (`ClaudeConnector`: claude.ai members and invites through the session cookie), `mapping.py` (`member_to_account`, `invite_to_account`, `pick_organization`).
- `chatgpt/`, no map: `connector.py` (`ChatGptConnector`: chatgpt.com session token, `/backend-api`; may hit Cloudflare), `mapping.py` (`user_to_account`, `invite_to_account`, `pick_workspace`).
- `browser_fake/`: own AGENTS.md. `connector.py` (`BrowserFakeConnector`: the app's own fake panel `api/dev_panel.py` through the real browser; reads with `fetch()`, writes with the click recipe), `recipe.json` (click recipe: `create_account`, `delete_account`), `admin_page.py` (`render_admin_page`: users table, row menu, dialogs; look version 2 renames the buttons), `mapping.py` (`panel_users`, `parse_page`), `panel_state.py` (invited and removed users and the look version in Redis).

Claude, ChatGPT and Slack endpoints are not verified on a real workspace; they are constants at the top of each `connector.py`.
