"""Socket Mode: Slack pushes events over a WebSocket, so the agent needs no public URL.

``apps.connections.open`` (app-level token) gives a one-off ``wss://`` URL.
Every envelope with an ``envelope_id`` is acknowledged at once (Slack retries
after 3 s) and handled in a background task. A ``disconnect`` message or a
dropped socket opens a new connection.
"""

import asyncio
import json
from collections.abc import Awaitable, Callable
from typing import Any

import structlog
from websockets.asyncio.client import connect
from websockets.exceptions import WebSocketException

from app.slack_agent import web_api
from app.slack_agent.web_api import SlackApiError

logger = structlog.get_logger()

MAX_BACKOFF_SECONDS = 60
AUTH_RETRY_SECONDS = 300

EnvelopeHandler = Callable[[dict[str, Any]], Awaitable[None]]
StateHandler = Callable[[str | None], Awaitable[None]]  # None: connected, text: the error


class SocketModeConnection:
    def __init__(self, app_token: str, on_envelope: EnvelopeHandler, on_state: StateHandler) -> None:
        self._app_token = app_token
        self._on_envelope = on_envelope
        self._on_state = on_state
        self._tasks: set[asyncio.Task[None]] = set()

    async def run(self) -> None:
        """Runs until cancelled, reconnecting with backoff."""
        backoff = 1
        while True:
            try:
                await self._session()
                backoff = 1
                continue  # Slack asked to reconnect
            except asyncio.CancelledError:
                raise
            except SlackApiError as exc:
                if exc.is_auth:
                    await self._on_state(
                        f"Slack rejected the app-level token ({exc.error}). Generate a new xapp- token and paste it."
                    )
                    await asyncio.sleep(AUTH_RETRY_SECONDS)  # a pasted token fixes it; the runner restarts us
                    continue
                await self._on_state(str(exc))
            except (OSError, WebSocketException, ValueError) as exc:
                await self._on_state(f"Socket Mode connection dropped: {exc}")
            await asyncio.sleep(backoff)
            backoff = min(backoff * 2, MAX_BACKOFF_SECONDS)

    async def _session(self) -> None:
        body = await web_api.call("apps.connections.open", self._app_token)
        async with connect(str(body["url"]), ping_interval=30, ping_timeout=30, max_size=4 * 1024 * 1024) as socket:
            async for raw in socket:
                message = json.loads(raw)
                kind = message.get("type")
                if kind == "hello":
                    await self._on_state(None)
                    continue
                if kind == "disconnect":
                    logger.info("slack_socket_disconnect", reason=message.get("reason"))
                    return
                envelope_id = message.get("envelope_id")
                if envelope_id:
                    await socket.send(json.dumps({"envelope_id": envelope_id}))
                self._spawn(message)

    def _spawn(self, envelope: dict[str, Any]) -> None:
        task = asyncio.create_task(self._handle(envelope))
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)

    async def _handle(self, envelope: dict[str, Any]) -> None:
        try:
            await self._on_envelope(envelope)
        except Exception:
            logger.exception("slack_envelope_failed", type=envelope.get("type"))
