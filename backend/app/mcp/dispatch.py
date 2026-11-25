"""Runs a tool: the same HTTP request the panel would send, made in-process to the FastAPI app.

Going through the API (not the services) keeps every rule of the panel: validation, the role and
scope checks, error codes and the audit log, which names the token's owner.
"""

import base64
import json
from typing import TYPE_CHECKING, Any
from urllib.parse import quote, urlsplit

import httpx
import mcp_types as types

from app.api.auth_deps import CLIENT_HEADER
from app.config import settings
from app.mcp.catalog import BodyMode

if TYPE_CHECKING:
    from fastapi import FastAPI

    from app.mcp.catalog import ToolSpec

TIMEOUT_SECONDS = 120.0


class ApiDispatcher:
    def __init__(self, app: FastAPI) -> None:
        # The Host must be one the API answers to (AllowedHostsMiddleware): the panel's own.
        host = urlsplit(settings.public_url).netloc or "localhost"
        self.client = httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url=f"http://{host}", timeout=TIMEOUT_SECONDS
        )

    async def aclose(self) -> None:
        await self.client.aclose()

    async def call(self, spec: ToolSpec, arguments: dict[str, Any], token: str) -> types.CallToolResult:
        unknown = set(arguments) - set(spec.input_schema["properties"])
        if unknown:
            return _error(f"Unknown arguments: {', '.join(sorted(unknown))}. See the tool's input schema.")
        missing = [name for name in spec.path_params if arguments.get(name) in (None, "")]
        if missing:
            return _error(f"Missing arguments: {', '.join(missing)}.")
        path = spec.path
        for name in spec.path_params:
            path = path.replace(f"{{{name}}}", quote(str(arguments[name]), safe=""))
        params = {name: arguments[name] for name in spec.query_params if arguments.get(name) is not None}
        request: dict[str, Any] = {"params": params}
        if spec.body_mode == BodyMode.JSON_FIELDS:
            request["json"] = {name: arguments[name] for name in spec.body_fields if name in arguments}
        elif spec.body_mode == BodyMode.JSON_BODY and "body" in arguments:
            request["json"] = arguments["body"]
        elif spec.body_mode == BodyMode.MULTIPART:
            request["files"] = {
                name: (f"{name}.txt", str(arguments[name]).encode(), "text/plain")
                for name in spec.file_fields
                if name in arguments
            }
            request["data"] = {
                name: str(arguments[name])
                for name in spec.body_fields
                if name in arguments and name not in spec.file_fields
            }
        headers = {"Authorization": f"Bearer {token}", CLIENT_HEADER: "mcp"}
        response = await self.client.request(spec.method, path, headers=headers, **request)
        return _result(response)


def _result(response: httpx.Response) -> types.CallToolResult:
    content_type = response.headers.get("content-type", "")
    if response.status_code >= 400:
        return _error(f"HTTP {response.status_code}: {_error_detail(response)}")
    if response.status_code == 204 or not response.content:
        return types.CallToolResult(content=[types.TextContent(type="text", text="Done.")])
    if content_type.startswith("image/"):
        data = base64.b64encode(response.content).decode()
        mime = content_type.split(";")[0]
        return types.CallToolResult(content=[types.ImageContent(type="image", data=data, mime_type=mime)])
    if "json" in content_type:
        text = json.dumps(response.json(), ensure_ascii=False, separators=(",", ":"))
    else:
        text = response.text
    return types.CallToolResult(content=[types.TextContent(type="text", text=text)])


def _error_detail(response: httpx.Response) -> str:
    try:
        detail = response.json().get("detail")
    except ValueError, AttributeError:
        return response.text[:2000] or response.reason_phrase
    if isinstance(detail, list):  # FastAPI validation errors
        return "; ".join(f"{_argument(item.get('loc', []))}: {item.get('msg')}" for item in detail)
    return str(detail)


def _argument(location: list) -> str:
    """``["body", "last_name"]`` is the argument ``last_name``: tools take one flat object."""
    parts = location[1:] if location and location[0] in ("body", "query", "path") else location
    return ".".join(str(part) for part in parts) or "arguments"


def _error(message: str) -> types.CallToolResult:
    return types.CallToolResult(content=[types.TextContent(type="text", text=message)], is_error=True)
