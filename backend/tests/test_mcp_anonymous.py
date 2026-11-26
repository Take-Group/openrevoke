"""MCP without a token: connect and list the tools, never call one (``app/mcp/server.py``)."""

import json
from typing import Any

import pytest

from app.mcp.server import McpEndpoint, _listing_only


def _rpc(method: str, **extra: Any) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": 1, "method": method, **extra}


@pytest.mark.parametrize(
    "payload",
    [
        _rpc("initialize", params={}),
        _rpc("tools/list"),
        _rpc("ping"),
        {"jsonrpc": "2.0", "method": "notifications/initialized"},
        [_rpc("initialize"), {"jsonrpc": "2.0", "method": "notifications/initialized"}],
    ],
)
def test_listing_messages_pass(payload: Any) -> None:
    assert _listing_only(json.dumps(payload).encode())


@pytest.mark.parametrize(
    "body",
    [
        json.dumps(_rpc("tools/call", params={"name": "get_overview"})).encode(),
        json.dumps([_rpc("tools/list"), _rpc("tools/call", params={"name": "start_offboarding"})]).encode(),
        json.dumps(_rpc("resources/read")).encode(),
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


async def test_anonymous_tool_call_gets_401_and_never_reaches_the_server() -> None:
    mcp = _Mcp()
    body = json.dumps(_rpc("tools/call", params={"name": "approve_offboarding", "arguments": {}})).encode()
    assert await _post(McpEndpoint(mcp), body) == 401  # type: ignore[arg-type]
    assert mcp.manager.handled == []


async def test_large_anonymous_body_gets_401() -> None:
    mcp = _Mcp()
    body = json.dumps(_rpc("tools/list", params={"pad": "x" * 70_000})).encode()
    assert await _post(McpEndpoint(mcp), body) == 401  # type: ignore[arg-type]
    assert mcp.manager.handled == []
