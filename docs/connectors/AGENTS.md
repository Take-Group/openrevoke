# open-revoke/docs/connectors/

One page per connector: key, method (API or browser), how to connect, endpoints, limits and what is still unverified. Code of each connector is `backend/app/connectors/<key>/`. Browser connectors (`chatgpt`, `claude`, `slack`) have all addresses as constants at the top of their `connector.py` and are marked as not verified on a real account.

- `chatgpt.md`: key `chatgpt`, browser session; Cloudflare anti-bot risk; Enterprise should use `scim`.
- `claude-team.md`: key `claude`, browser session of an Owner or Admin; optional `org_uuid` for several organizations; Enterprise should use `scim`.
- `github.md`: key `github`, REST API with a fine-grained or classic token; reads org members and pending invites, invites by e-mail, removes members.
- `google_workspace.md`: key `google_workspace`, Admin SDK Directory API; connects with Google OAuth (default) or a service-account key with domain-wide delegation; suspends, never deletes; can be the people source.
- `scim.md`: key `scim`, SCIM 2.0 client for any app with a `/Users` endpoint; config `base_url`, `token`, `user_filter`, `delete_mode` (`deactivate` or `delete`), `page_size`.
- `slack.md`: key `slack`, browser session of a Workspace Admin or Owner; config `workspace` (subdomain); plans with SCIM should use `scim`.
