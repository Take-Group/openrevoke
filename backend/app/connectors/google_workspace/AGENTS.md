# open-revoke/backend/app/connectors/google_workspace/

Google Workspace: Admin SDK Directory API (accounts, people, create, suspend) and app discovery (Reports API audit plus token inventory). Two ways to authenticate: service account with domain-wide delegation, or an admin's OAuth refresh token.

- `__init__.py`: empty.
- `connector.py`: `GoogleWorkspaceConnector`, `GoogleWorkspaceConfig`; all five capabilities; `delete_suspends = True`; picks service account or OAuth credentials per call.
- `auth.py`: service account path: `parse_service_account`, `build_assertion` (RS256 JWT), `fetch_access_token`, `access_token(ctx, scope)`.
- `oauth.py`: OAuth path with PKCE: `authorization_url`, `exchange_code`, `refreshed_token`, `fetch_email`. Each installation uses its own OAuth client. Revoked admin means `needs_login`.
- `scopes.py`: `SCOPE_READ`, `SCOPE_WRITE`, `SCOPE_AUDIT`, `SCOPE_TOKENS`, `is_granted` (write covers read).
- `mapping.py`: pure parsing of `users.list` and `users.insert`: `parse_users_page`, `user_to_account`, `user_to_person`, `user_aliases`, `employee_id`, `manager_email` (`relations` type manager), `primary_organization` (department, title).
- `discovery.py`: `GoogleWorkspaceConnector.discover_apps` helpers: `read_activities` (Reports API `authorize` and `DELETE_USER`, 180 days max), `read_token_inventory` (optional scope), `directory_users`.
- `discovery_mapping.py`: pure parsing for discovery: `GrantBook` (merges events into `AppGrant`), `deleted_user`, `parse_page`, `is_google_owned`.
