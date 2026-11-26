# open-revoke/backend/app/mcp/

MCP server for AI assistants at `/mcp` (skill `skills/backend/mcp.md`). Default toolset: task tools (`agent/`); `?toolset=api`: one tool per API route. A call is an in-process HTTP request to the API with the caller's API token, so the panel's rules apply. Without a token a client may only connect and list tools; a tool call answers how to add a token.

- `__init__.py`: empty.
- `address.py`: `MCP_PATH` (`/mcp`), `mcp_url()` from `PUBLIC_URL`.
- `policy.py`: `EXCLUDED` (operation id and why), `PUBLIC_ALLOWED`, `DESTRUCTIVE`, `DEFAULT_TAG`. The only file to edit to keep an endpoint out or mark it destructive.
- `catalog.py`: `build_catalog(app)` returns `ToolSpec`s (`Access` admin/user/public from route dependencies, `BodyMode` of the request body); cookie-only routes are left out.
- `schema.py`: `SchemaResolver` (inlines `$ref`, drops titles), `is_file`.
- `caller.py`: `Caller` (token, role, scope, tags, `Toolset`; `anonymous` without a token), `current_caller` context var, `authenticate(authorization, tags, toolset)`, `anonymous(tags, toolset)`.
- `dispatch.py`: `ApiDispatcher.call(spec, arguments, token)`: request through `httpx.ASGITransport`, response as MCP content.
- `server.py`: `OpenRevokeMcp` (SDK lowlevel `Server`, `tools_for(caller)` of either toolset, stateless JSON session manager, `run()` for the lifespan), `McpEndpoint` (ASGI app: no token only `ANONYMOUS_METHODS`, a tool call then is a tool error, else 401; `?tags=`, `?toolset=`).
- `agent/`: own AGENTS.md. Task tools for assistants: one per task of the panel, for admins and members.
- `instructions.py`: `INSTRUCTIONS` the client reads at connect: domain, the order of writes (look, create actions, approve, follow), the approve rule. Name only tools that exist.
