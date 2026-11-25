"""The MCP server at ``/api/mcp``: Streamable HTTP, stateless, plain JSON responses.

Stateless JSON works through any proxy (the panel's Next.js rewrite, Caddy) and needs no sticky
sessions. ``McpEndpoint`` checks the API token, then the SDK's session manager runs the request;
the tool handlers read the caller from ``current_caller``.
"""

from contextlib import asynccontextmanager
from typing import TYPE_CHECKING, Any
from urllib.parse import parse_qs

import mcp_types as types
from mcp.server.lowlevel import Server
from mcp.server.streamable_http_manager import StreamableHTTPSessionManager
from starlette.responses import JSONResponse

from app.config import settings
from app.mcp.caller import Caller, authenticate, current_caller
from app.mcp.catalog import Access, ToolSpec, build_catalog
from app.mcp.dispatch import ApiDispatcher
from app.mcp.instructions import INSTRUCTIONS
from app.models.enums import ApiTokenScope, UserRole

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from fastapi import FastAPI
    from starlette.types import Receive, Scope, Send


class OpenRevokeMcp:
    def __init__(self, app: FastAPI) -> None:
        self.app = app
        self._catalog: dict[str, ToolSpec] | None = None
        self.dispatcher = ApiDispatcher(app)
        self.server = Server(
            "open-revoke",
            version=settings.version,
            title="Open Revoke",
            instructions=INSTRUCTIONS,
            on_list_tools=self._list_tools,
            on_call_tool=self._call_tool,
        )
        self.manager = StreamableHTTPSessionManager(app=self.server, json_response=True, stateless=True)

    @asynccontextmanager
    async def run(self) -> AsyncIterator[None]:
        async with self.manager.run():
            try:
                yield
            finally:
                await self.dispatcher.aclose()

    @property
    def catalog(self) -> dict[str, ToolSpec]:
        """Built on first use: every router is mounted by then."""
        if self._catalog is None:
            self._catalog = {spec.name: spec for spec in build_catalog(self.app)}
        return self._catalog

    def tools_for(self, caller: Caller) -> list[ToolSpec]:
        return [spec for spec in self.catalog.values() if _visible(spec, caller)]

    async def _list_tools(self, ctx: Any, params: types.PaginatedRequestParams | None) -> types.ListToolsResult:
        caller = _require_caller()
        return types.ListToolsResult(tools=[_tool(spec) for spec in self.tools_for(caller)])

    async def _call_tool(self, ctx: Any, params: types.CallToolRequestParams) -> types.CallToolResult:
        caller = _require_caller()
        spec = self.catalog.get(params.name)
        if spec is None or not _visible(spec, caller):
            text = f"Unknown tool {params.name}, or the token cannot use it (role {caller.role}, {caller.scope})."
            return types.CallToolResult(content=[types.TextContent(type="text", text=text)], is_error=True)
        return await self.dispatcher.call(spec, dict(params.arguments or {}), caller.token)


class McpEndpoint:
    """ASGI app of ``/api/mcp``: 401 without a valid API token, else the MCP request."""

    def __init__(self, mcp: OpenRevokeMcp) -> None:
        self.mcp = mcp

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        headers = {name.decode("latin-1").lower(): value.decode("latin-1") for name, value in scope["headers"]}
        query = parse_qs(scope.get("query_string", b"").decode())
        caller = await authenticate(headers.get("authorization"), (query.get("tags") or [None])[0])
        if caller is None:
            response = JSONResponse(
                {"detail": "Send a personal API token: Authorization: Bearer orv_... (Settings, API and MCP)."},
                status_code=401,
                headers={"WWW-Authenticate": 'Bearer realm="open-revoke"'},
            )
            await response(scope, receive, send)
            return
        reset = current_caller.set(caller)
        try:
            await self.mcp.manager.handle_request(scope, receive, send)
        finally:
            current_caller.reset(reset)


def _require_caller() -> Caller:
    caller = current_caller.get()
    if caller is None:  # McpEndpoint always sets it; a missing one is a bug
        raise RuntimeError("MCP request without a caller")
    return caller


def _visible(spec: ToolSpec, caller: Caller) -> bool:
    if spec.access == Access.ADMIN and caller.role != UserRole.ADMIN:
        return False
    if caller.scope == ApiTokenScope.READ and not spec.read_only:
        return False
    return caller.tags is None or spec.tag in caller.tags


def _tool(spec: ToolSpec) -> types.Tool:
    annotations = types.ToolAnnotations(
        title=spec.title,
        read_only_hint=spec.read_only,
        destructive_hint=spec.destructive,
        idempotent_hint=spec.method in ("GET", "PUT", "DELETE"),
        open_world_hint=False,
    )
    return types.Tool(
        name=spec.name,
        title=spec.title,
        description=spec.description,
        input_schema=spec.input_schema,
        annotations=annotations,
    )
