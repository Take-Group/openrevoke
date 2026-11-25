# open-revoke/backend/app/mcp/

MCP server for AI assistants at `/api/mcp` (skill `skills/backend/mcp.md`). Tools are built from the FastAPI routes; a call is an in-process HTTP request to the API with the caller's API token, so the panel's rules apply.

- `__init__.py`: empty.
- `address.py`: `MCP_PATH` (`/api/mcp`), `mcp_url()` from `PUBLIC_URL`.
- `policy.py`: `EXCLUDED` (operation id and why), `PUBLIC_ALLOWED`, `DESTRUCTIVE`, `DEFAULT_TAG`. The only file to edit to keep an endpoint out or mark it destructive.
- `catalog.py`: `build_catalog(app)` returns `ToolSpec`s (`Access` admin/user/public from route dependencies, `BodyMode` of the request body); cookie-only routes are left out.
- `schema.py`: `SchemaResolver` (inlines `$ref`, drops titles), `is_file`.
- `caller.py`: `Caller` (token, role, scope, tags), `current_caller` context var, `authenticate(authorization, tags)`.
- `dispatch.py`: `ApiDispatcher.call(spec, arguments, token)`: request through `httpx.ASGITransport`, response as MCP content.
- `server.py`: `OpenRevokeMcp` (SDK lowlevel `Server`, `tools_for(caller)`, stateless JSON session manager, `run()` for the lifespan), `McpEndpoint` (ASGI app: 401 without a token, `?tags=`).
- `instructions.py`: `INSTRUCTIONS` the client reads at connect: domain and the approve rules.
