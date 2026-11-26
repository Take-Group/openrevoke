# Skill: MCP server and API tokens

## What it does

AI assistants (Claude Code, Codex, Cursor) connect to Open Revoke over MCP and do what a panel
user can do: add people, connect apps, sync, offboard. The server lives in the API process at
`/mcp` (Streamable HTTP, stateless, plain JSON responses), on the panel's origin, so
self-hosting needs no extra port: the panel's Next.js rewrite (`frontend/next.config.ts`) passes
`/mcp` to the API, and Caddy, Ingress or any other proxy forward everything to the panel.

Two toolsets:

- **Task tools** (default, admins): a dozen tools named after what an admin asks
  (`app/mcp/agent/`): `get_overview`, `get_spend_by_app`, `get_app_access`,
  `list_discovered_apps`, `find_people`, `get_person_access`, `list_leavers_with_access`,
  `plan_offboarding`, `start_offboarding`, `approve_offboarding`, `get_offboarding_status`,
  `list_pending_approvals`. Each composes a few API calls and returns compact JSON with names,
  money as `"12.50 EUR"` and a `next` hint. People and apps are referenced by e-mail, name or id.
- **API tools** (`?toolset=api`, and every non-admin caller): one tool per API operation, built
  from the FastAPI routes at the first request.

Without a token a client may connect and list the tools (`initialize`, `ping`, `tools/list`,
notifications): registries and people who have not installed anything see what the server
offers. Every other request without a token, a tool call above all, gets HTTP 401 before it
reaches the SDK; a wrong token is always 401. The anonymous view is the admin view with a write
token.

Every tool, of either set, goes through the API. A tool call is the same HTTP request the panel sends, made in-process
(`httpx.ASGITransport`) with the caller's token: validation, role and scope checks, error codes
and the audit log are the panel's own. A new endpoint becomes a tool with no change here.

The caller authenticates with a personal API token (`Authorization: Bearer orv_...`). The same
token works for the REST API. Tokens are managed in Settings, API and MCP (`/settings/api`).

## Files

| File | What it decides |
|---|---|
| `backend/app/mcp/policy.py` | `EXCLUDED` operations (with the reason), `PUBLIC_ALLOWED`, `DESTRUCTIVE` (beyond DELETE) |
| `backend/app/mcp/catalog.py` | `build_catalog`: one `ToolSpec` per operation; access from the route's dependencies (`require_admin` admin, `get_current_user` every role, `get_current_session` never a tool); flat input (path, query, JSON body fields; multipart file fields as text) |
| `backend/app/mcp/schema.py` | `SchemaResolver`: inlines `$ref`, drops titles |
| `backend/app/mcp/dispatch.py` | `ApiDispatcher.call`: builds the request, maps the response (JSON as text, images as image content, `HTTP <code>: <detail>` errors with flat argument names) |
| `backend/app/mcp/server.py` | `OpenRevokeMcp` (SDK `Server`, both toolsets, list and call handlers, session manager), `McpEndpoint` (anonymous listing, 401 for the rest, `?tags=`, `?toolset=`), tool annotations |
| `backend/app/mcp/agent/` | task tools: `base.py` (`AgentTool`, `ToolError`), `api.py` (`AgentApi`: in-process API calls, person and app lookup), `views.py` (compact shapes), `people.py`, `apps.py`, `offboarding.py` (one `TOOLS` tuple each), `registry.py` (`AGENT_TOOLS`, `call`) |
| `backend/app/mcp/caller.py` | `Caller` (with `Toolset`), `current_caller`, `authenticate`, `anonymous` |
| `backend/app/mcp/instructions.py` | `INSTRUCTIONS`: what the assistant reads first: domain, approve rules |
| `backend/app/mcp/address.py` | `MCP_PATH`, `mcp_url()` (from `PUBLIC_URL`) |
| `backend/app/main.py` | mounts `McpEndpoint` at `MCP_PATH`, runs the session manager in `lifespan` |
| `backend/app/models/api_token.py` | `ApiToken`: SHA-256 of the token, `prefix`, `scope` (`ApiTokenScope` read or write), `last_used_at` |
| `backend/app/services/auth/api_tokens.py` | `create`, `list_for_user`, `revoke`, `authenticate` (owner must be active), `actor_name` |
| `backend/app/api/auth_deps.py` | `get_current_user` takes a bearer token before the cookie; a read token gets only GET; audit actor `email (API token: name)` |
| `backend/app/api/api_tokens.py` | GET/POST/DELETE `/api/api-tokens`, panel session only (a token cannot manage tokens) |
| `backend/app/db/seed.py` | `DEV_API_TOKENS`: fixed local tokens `orv_dev_admin_local_only`, `orv_dev_member_local_only` (only with `OPEN_REVOKE_DEV_PREFILL`) |
| `frontend/src/components/api-tokens/` | `/settings/api` list and setup snippets, `/settings/api/new` form and the one-time token |

## Who sees which tools

| Caller | Tools |
|---|---|
| no token | the admin's list; every call 401 |
| admin, write token | the task tools; `?toolset=api`: every API tool (about 100) |
| admin, read token | read-only task tools; `?toolset=api`: GET tools only |
| user (not admin) | API tools: `/api/me` and the public catalog and currencies |
| `?toolset=api&tags=people,apps` | only API tools of those OpenAPI tags |

Tool annotations: task tools set `readOnlyHint` and `destructiveHint` themselves
(`start_offboarding`, `approve_offboarding`); API tools get `readOnlyHint` for GET,
`destructiveHint` for DELETE and `policy.DESTRUCTIVE`.
Clients use them to ask before a call; keep `DESTRUCTIVE` up to date when an endpoint removes
accounts in other apps.

## Adding a task tool

A tool answers one question an admin asks, in one call. Add an `AgentTool` to the `TOOLS` of the
module it belongs to (or a new module listed in `registry.py`). The handler calls the API through
`AgentApi`, never a service, raises `ToolError` with what to call instead, and returns names
rather than ids where a person reads them. A tool that writes in other apps is `destructive` and
its description says to ask the user first.

## Adding or changing an endpoint

- Write the endpoint's docstring for an AI reader: the tool description is
  `"<summary>. <docstring>"`. Say what it changes, what runs in the background and what to call next.
- Describe query parameters and body fields with `Field(description=...)`: they become argument
  descriptions.
- Keep an operation out of MCP only with a reason in `policy.EXCLUDED` (secrets that must not reach
  a model provider, browser redirects, binary uploads).
- A cookie-only route (`CurrentSessionDep`) never becomes a tool.

## Checking

```bash
# tools without a token (the admin's list), then a call: 401
curl -s http://localhost:18410/mcp -H 'Content-Type: application/json' \
  -H 'Accept: application/json, text/event-stream' -d '{"jsonrpc":"2.0","id":1,"method":"tools/list"}'
# tools of the seeded admin token (dev stack)
curl -s http://localhost:18410/mcp -H 'Content-Type: application/json' \
  -H 'Accept: application/json, text/event-stream' -H 'MCP-Protocol-Version: 2025-06-18' \
  -H 'Authorization: Bearer orv_dev_admin_local_only' \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list"}'
# Claude Code
claude mcp add --transport http open-revoke http://localhost:18410/mcp \
  --header "Authorization: Bearer orv_dev_admin_local_only"
```

## Not yet

- OAuth sign-in for MCP clients (dynamic client registration, consent page) instead of pasted tokens.
- Token expiry dates.
- A clearer refusal for anonymous tool calls: Claude Code shows the 401 as "session expired" and
  reconnects, without the message about the token.
- Task tools for onboarding and connecting apps (today: `?toolset=api`).
