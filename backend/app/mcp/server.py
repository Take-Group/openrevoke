"""The MCP server at ``/mcp``: Streamable HTTP, stateless, plain JSON responses.

Stateless JSON works through any proxy (the panel's Next.js rewrite, Caddy) and needs no sticky
sessions. ``McpEndpoint`` checks the API token, then the SDK's session manager runs the request;
the tool handlers read the caller from ``current_caller``.

Two toolsets: the task tools of ``app/mcp/agent/`` (default; admins get the company's tools,
members their own access and approvals) and one tool per API operation (``?toolset=api``).
"""

import json
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING, Any
from urllib.parse import parse_qs

import mcp_types as types
from mcp.server.lowlevel import Server
from mcp.server.streamable_http_manager import StreamableHTTPSessionManager
from starlette.responses import JSONResponse

from app.config import settings
from app.mcp.agent.api import AgentApi
from app.mcp.agent.registry import AGENT_TOOLS
from app.mcp.agent.registry import call as call_agent_tool
from app.mcp.caller import Caller, Toolset, anonymous, authenticate, current_caller
from app.mcp.catalog import Access, ToolSpec, build_catalog
from app.mcp.dispatch import ApiDispatcher
from app.mcp.instructions import INSTRUCTIONS
from app.models.enums import ApiTokenScope, UserRole

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from fastapi import FastAPI
    from starlette.types import Message, Receive, Scope, Send

    from app.mcp.agent.base import AgentTool

# JSON-RPC methods a caller without a token may send. A tool call is let through only to be refused
# as a tool error by ``_call_tool`` (it reaches no API): an HTTP 401 there makes clients drop the
# session ("session expired" in Claude Code) and the user never reads why. Anything else gets 401.
ANONYMOUS_METHODS = frozenset({"initialize", "ping", "tools/list", "tools/call"})
MAX_ANONYMOUS_BODY = 64 * 1024
UNAUTHORIZED = "Send a personal API token: Authorization: Bearer orv_... (Settings, API and MCP)."
ANONYMOUS_CALL = (
    "This Open Revoke MCP server needs a personal API token to run tools; listing them works without one. "
    "Create a token in the panel (Settings, API and MCP) and add the header Authorization: Bearer orv_... "
    "to this server in your MCP client, then reconnect."
)


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

    def tools_for(self, caller: Caller) -> list[types.Tool]:
        if _uses_agent_tools(caller):
            return [_agent_tool(tool) for tool in AGENT_TOOLS.values() if _agent_visible(tool, caller)]
        return [_api_tool(spec) for spec in self.catalog.values() if _visible(spec, caller)]

    async def _list_tools(self, ctx: Any, params: types.PaginatedRequestParams | None) -> types.ListToolsResult:
        return types.ListToolsResult(tools=self.tools_for(_require_caller()))

    async def _call_tool(self, ctx: Any, params: types.CallToolRequestParams) -> types.CallToolResult:
        caller = _require_caller()
        arguments = dict(params.arguments or {})
        if caller.anonymous:  # before any lookup: an anonymous call never reaches the API
            return _error(ANONYMOUS_CALL)
        if _uses_agent_tools(caller):
            tool = AGENT_TOOLS.get(params.name)
            if tool is None or not _agent_visible(tool, caller):
                return _error(_unknown(params.name, caller))
            return await call_agent_tool(tool, AgentApi(self.dispatcher.client, caller.token), arguments)
        spec = self.catalog.get(params.name)
        if spec is None or not _visible(spec, caller):
            return _error(_unknown(params.name, caller))
        return await self.dispatcher.call(spec, arguments, caller.token)


class McpEndpoint:
    """ASGI app of ``/mcp``. No token: connect, list tools, a tool call answered with an error; 401 for the rest.

    A wrong token is always 401: only a request without ``Authorization`` is anonymous.
    """

    def __init__(self, mcp: OpenRevokeMcp) -> None:
        self.mcp = mcp

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        headers = {name.decode("latin-1").lower(): value.decode("latin-1") for name, value in scope["headers"]}
        query = parse_qs(scope.get("query_string", b"").decode())
        tags, toolset = (query.get("tags") or [None])[0], (query.get("toolset") or [None])[0]
        authorization = headers.get("authorization")
        if authorization:
            caller = await authenticate(authorization, tags, toolset)
        elif scope["method"] == "POST":
            body = await _read_body(receive, MAX_ANONYMOUS_BODY)
            caller = anonymous(tags, toolset) if body is not None and _listing_only(body) else None
            receive = _replay(body or b"")
        else:
            caller = None
        if caller is None:
            await _unauthorized(scope, receive, send)
            return
        reset = current_caller.set(caller)
        try:
            await self.mcp.manager.handle_request(scope, receive, send)
        finally:
            current_caller.reset(reset)


async def _read_body(receive: Receive, limit: int) -> bytes | None:
    """The whole request body, or None when it is longer than ``limit``."""
    chunks: list[bytes] = []
    size = 0
    while True:
        message = await receive()
        if message["type"] != "http.request":
            return None
        chunk = message.get("body", b"")
        size += len(chunk)
        if size > limit:
            return None
        chunks.append(chunk)
        if not message.get("more_body", False):
            return b"".join(chunks)


def _replay(body: bytes) -> Receive:
    sent = False

    async def receive() -> Message:
        nonlocal sent
        if sent:
            return {"type": "http.disconnect"}
        sent = True
        return {"type": "http.request", "body": body, "more_body": False}

    return receive


def _listing_only(body: bytes) -> bool:
    """True when every JSON-RPC message only connects, pings or lists tools (or is a notification)."""
    try:
        payload = json.loads(body)
    except ValueError:
        return False
    messages = payload if isinstance(payload, list) else [payload]
    for message in messages:
        if not isinstance(message, dict):
            return False
        method = message.get("method")
        if method is None:  # a response from the client: nothing to run
            continue
        if not isinstance(method, str):
            return False
        if method not in ANONYMOUS_METHODS and not method.startswith("notifications/"):
            return False
    return bool(messages)


async def _unauthorized(scope: Scope, receive: Receive, send: Send) -> None:
    response = JSONResponse(
        {"detail": UNAUTHORIZED},
        status_code=401,
        headers={"WWW-Authenticate": 'Bearer realm="open-revoke"'},
    )
    await response(scope, receive, send)


def _require_caller() -> Caller:
    caller = current_caller.get()
    if caller is None:  # McpEndpoint always sets it; a missing one is a bug
        raise RuntimeError("MCP request without a caller")
    return caller


def _uses_agent_tools(caller: Caller) -> bool:
    return caller.toolset == Toolset.AGENT


def _agent_visible(tool: AgentTool, caller: Caller) -> bool:
    if caller.anonymous:  # the listing shows every tool, an admin's and a member's
        return True
    audience = "admin" if caller.role == UserRole.ADMIN else "user"
    return tool.audience == audience and (caller.scope != ApiTokenScope.READ or tool.read_only)


def _visible(spec: ToolSpec, caller: Caller) -> bool:
    if spec.access == Access.ADMIN and caller.role != UserRole.ADMIN:
        return False
    if caller.scope == ApiTokenScope.READ and not spec.read_only:
        return False
    return caller.tags is None or spec.tag in caller.tags


def _unknown(name: str, caller: Caller) -> str:
    return f"Unknown tool {name}, or the token cannot use it (role {caller.role}, {caller.scope}, {caller.toolset})."


def _error(text: str) -> types.CallToolResult:
    return types.CallToolResult(content=[types.TextContent(type="text", text=text)], is_error=True)


def _agent_tool(tool: AgentTool) -> types.Tool:
    annotations = types.ToolAnnotations(
        title=tool.title,
        read_only_hint=tool.read_only,
        destructive_hint=tool.destructive,
        idempotent_hint=tool.read_only,
        open_world_hint=tool.destructive,  # removals reach other apps
    )
    return types.Tool(
        name=tool.name,
        title=tool.title,
        description=tool.description,
        input_schema=tool.input_schema,
        annotations=annotations,
    )


def _api_tool(spec: ToolSpec) -> types.Tool:
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
