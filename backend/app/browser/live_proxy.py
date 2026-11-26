"""Live view of the shared browser, passed through the API.

The browser container serves noVNC (``docker/browser/live.html`` and the modules it
imports) and the VNC WebSocket on port 6080 (websockify). No port of the container is
published on the host. The panel loads ``/api/browser/live/live.html`` on its own origin;
the API fetches the file from the container and pipes ``/api/browser/live/websockify``
both ways (``api/browser_live.py`` checks the session). So the live view gets the panel's
sign-in and the panel's HTTPS, wherever the panel runs.
"""

import asyncio
import contextlib
import re
from dataclasses import dataclass

import httpx
import structlog
from starlette.websockets import WebSocket, WebSocketDisconnect, WebSocketState
from websockets.asyncio.client import connect
from websockets.exceptions import ConnectionClosed, InvalidHandshake
from websockets.typing import Origin, Subprotocol

from app.config import settings
from app.services.errors import UnavailableError

logger = structlog.get_logger()

# websockify takes the WebSocket only from origins in NOVNC_ALLOWED_ORIGINS (ExpectOrigin).
# The browser image always adds this one (docker/browser/entrypoint.sh).
PROXY_ORIGIN = Origin("http://open-revoke-live-proxy")

# What the page needs: live.html and the ES modules of noVNC it imports. Nothing else of
# the container's web root (vnc.html with its settings menu) goes through.
_FILE = re.compile(r"^(?:live\.html|(?:core|vendor)/[A-Za-z0-9_\-/]+\.js)$")


@dataclass(frozen=True)
class LiveFile:
    content: bytes
    media_type: str


def _address() -> str:
    return f"{settings.browser_cdp_host}:{settings.browser_live_port}"


def is_live_file(path: str) -> bool:
    return bool(_FILE.match(path)) and ".." not in path


async def fetch_file(path: str) -> LiveFile | None:
    """A file of the live view from the browser container; None when it has no such file."""
    if not is_live_file(path):
        return None
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(f"http://{_address()}/{path}")
    except httpx.HTTPError as exc:
        raise UnavailableError(f"The browser container does not answer: {exc}") from exc
    if response.status_code != 200:
        return None
    return LiveFile(response.content, response.headers.get("content-type", "application/octet-stream"))


async def _to_panel(upstream, client: WebSocket) -> None:
    async for message in upstream:
        if isinstance(message, bytes):
            await client.send_bytes(message)
        else:
            await client.send_text(message)


async def _to_browser(client: WebSocket, upstream) -> None:
    while True:
        message = await client.receive()
        if message["type"] == "websocket.disconnect":
            return
        if message.get("bytes") is not None:
            await upstream.send(message["bytes"])
        elif message.get("text") is not None:
            await upstream.send(message["text"])


async def pipe(client: WebSocket) -> None:
    """Connects to websockify in the browser container and passes frames both ways until one side closes."""
    subprotocols = [Subprotocol(name) for name in client.scope.get("subprotocols", [])]
    try:
        upstream = await connect(
            f"ws://{_address()}/websockify",
            origin=PROXY_ORIGIN,
            subprotocols=subprotocols or None,
            compression=None,
            max_size=None,
            open_timeout=10,
        )
    except (OSError, InvalidHandshake, TimeoutError) as exc:
        logger.warning("Live view: browser container refused the WebSocket", error=str(exc))
        await client.close(code=1011)
        return
    async with upstream:
        await client.accept(subprotocol=upstream.subprotocol)
        tasks = [asyncio.create_task(_to_panel(upstream, client)), asyncio.create_task(_to_browser(client, upstream))]
        try:
            await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
        finally:
            for task in tasks:
                task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)
    if client.client_state == WebSocketState.CONNECTED:
        with contextlib.suppress(RuntimeError, WebSocketDisconnect, ConnectionClosed):
            await client.close()
