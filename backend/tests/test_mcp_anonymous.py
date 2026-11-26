"""MCP without a token: connect and list the tools; a tool call is a tool error (``app/mcp/server.py``)."""

import json
from typing import Any

import mcp_types as types
import pytest
from fastapi import FastAPI

from app.mcp.caller import anonymous, current_caller
from app.mcp.server import McpEndpoint, OpenRevokeMcp, _listing_only


def _rpc(method: str, **extra: Any) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": 1, "method": method, **extra}


@pytest.mark.parametrize(
    "payload",
    [
        _rpc("initialize", params={}),
        _rpc("tools/list"),
        _rpc("ping"),
        _rpc("tools/call", params={"name": "get_overview"}),
        {"jsonrpc": "2.0", "method": "notifications/initialized"},
        [_rpc("initialize"), {"jsonrpc": "2.0", "method": "notifications/initialized"}],
    ],
)
def test_listing_messages_pass(payload: Any) -> None:
    assert _listing_only(json.dumps(payload).encode())


@pytest.mark.parametrize(
    "body",
    [
        json.dumps(_rpc("resources/read")).encode(),
        json.dumps([_rpc("tools/list"), _rpc("prompts/get")]).encode(),
        json.dumps(_rpc(["tools/list"])).encode(),
        json.dumps([]).encode(),
        json.dumps(["tools/list"]).encode(),
        b"not json",
    ],
)
def test_everything_else_is_refused(body: bytes) -> None:
    assert not _listing_only(body)


class _Manager:
    def __init__(self) -> None:
        self.handled: list[bytes] = []

    async def handle_request(self, scope: Any, receive: Any, send: Any) -> None:
        message = await receive()
        self.handled.append(message["body"])
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b"{}"})


class _Mcp:
    def __init__(self) -> None:
        self.manager = _Manager()


async def _post(endpoint: McpEndpoint, body: bytes, headers: list[tuple[bytes, bytes]] | None = None) -> int:
    scope = {"type": "http", "method": "POST", "headers": headers or [], "query_string": b""}
    chunks = [{"type": "http.request", "body": body, "more_body": False}]
    sent: list[dict[str, Any]] = []

    async def receive() -> dict[str, Any]:
        return chunks.pop(0) if chunks else {"type": "http.disconnect"}

    async def send(message: dict[str, Any]) -> None:
        sent.append(message)

    await endpoint(scope, receive, send)
    return next(message["status"] for message in sent if message["type"] == "http.response.start")


async def test_anonymous_tool_list_reaches_the_server_with_its_body() -> None:
    mcp = _Mcp()
    body = json.dumps(_rpc("tools/list")).encode()
    assert await _post(McpEndpoint(mcp), body) == 200  # type: ignore[arg-type]
    assert mcp.manager.handled == [body]


async def test_anonymous_resource_read_gets_401_and_never_reaches_the_server() -> None:
    mcp = _Mcp()
    body = json.dumps(_rpc("resources/read", params={"uri": "x"})).encode()
    assert await _post(McpEndpoint(mcp), body) == 401  # type: ignore[arg-type]
    assert mcp.manager.handled == []


async def test_anonymous_tool_call_is_a_tool_error_without_an_api_request() -> None:
    server = OpenRevokeMcp(FastAPI())
    requests: list[object] = []
    server.dispatcher.client.request = lambda *a, **k: requests.append(a)  # type: ignore[method-assign]
    reset = current_caller.set(anonymous(None, None))
    try:
        for name in ("get_overview", "approve_actions", "start_offboarding"):
            result = await server._call_tool(None, types.CallToolRequestParams(name=name, arguments={}))
            assert result.is_error
            assert "API token" in result.content[0].text  # type: ignore[union-attr]
    finally:
        current_caller.reset(reset)
    assert requests == []


async def test_anonymous_listing_shows_admin_and_member_tools() -> None:
    names = {tool.name for tool in OpenRevokeMcp(FastAPI()).tools_for(anonymous(None, None))}
    assert {"get_overview", "start_offboarding", "approve_actions", "get_my_access"} <= names


async def test_large_anonymous_body_gets_401() -> None:
    mcp = _Mcp()
    body = json.dumps(_rpc("tools/list", params={"pad": "x" * 70_000})).encode()
    assert await _post(McpEndpoint(mcp), body) == 401  # type: ignore[arg-type]
    assert mcp.manager.handled == []
