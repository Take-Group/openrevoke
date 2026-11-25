"""Keeps the Slack agent running in the worker process.

Every ``POLL_SECONDS`` it reads the settings: new tokens, a new bot name or
"off" restart or stop the Socket Mode connection. While connected it also
sends approval requests to admins and results to the people who asked.
"""

import asyncio
import contextlib
import hashlib
from datetime import UTC, datetime
from typing import TYPE_CHECKING

import structlog
from sqlalchemy import update

from app.database import async_session
from app.models import SlackAgent
from app.models.enums import SlackAgentStatus
from app.services import slack_agent_secrets as tokens
from app.slack_agent import approvals, events, notifier
from app.slack_agent.runtime import SlackRuntime
from app.slack_agent.socket_mode import SocketModeConnection

if TYPE_CHECKING:
    from app.services.action_dispatch import ActionDispatcher

logger = structlog.get_logger()
POLL_SECONDS = 10


class SlackAgentRunner:
    def __init__(self, dispatcher: ActionDispatcher) -> None:
        self._dispatcher = dispatcher
        self._task: asyncio.Task[None] | None = None
        self._fingerprint: str | None = None
        self._runtime: SlackRuntime | None = None
        self._connected = False

    async def run_forever(self) -> None:
        while True:
            try:
                await self._tick()
            except asyncio.CancelledError:
                await self._stop()
                raise
            except Exception:
                logger.exception("slack_agent_tick_failed")
            await asyncio.sleep(POLL_SECONDS)

    async def _tick(self) -> None:
        async with async_session() as session:
            row = await session.get(SlackAgent, 1)
            values = tokens.read(row)
        bot_token, app_token = values.get(tokens.BOT_TOKEN), values.get(tokens.APP_TOKEN)
        wanted = row is not None and row.enabled and bool(bot_token) and bool(app_token)
        fingerprint = _fingerprint(row, bot_token, app_token) if wanted else None
        if fingerprint != self._fingerprint:
            await self._stop()
            self._fingerprint = fingerprint
            if wanted and row is not None and bot_token and app_token:
                self._start(row, bot_token, app_token)
        if self._connected and row is not None and row.status != SlackAgentStatus.CONNECTED:
            await self._set_state(None)  # the panel saved the same tokens again and reset the status
        if self._runtime is not None and self._connected:  # a broken token would fail every post
            await approvals.notify_pending(self._runtime)
            await notifier.notify_finished(self._runtime)

    def _start(self, row: SlackAgent, bot_token: str, app_token: str) -> None:
        runtime = SlackRuntime(
            bot_token=bot_token, bot_user_id=row.bot_user_id, bot_name=row.bot_name, dispatcher=self._dispatcher
        )

        async def on_envelope(envelope: dict) -> None:
            await events.handle_envelope(runtime, envelope)

        connection = SocketModeConnection(app_token, on_envelope, self._set_state)
        self._runtime = runtime
        self._task = asyncio.create_task(connection.run())
        logger.info("slack_agent_started", bot=row.bot_name)

    async def _stop(self) -> None:
        self._runtime = None
        self._connected = False
        if self._task is None:
            return
        self._task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await self._task
        self._task = None
        logger.info("slack_agent_stopped")

    async def _set_state(self, error: str | None) -> None:
        self._connected = error is None
        values: dict = {"status": SlackAgentStatus.CONNECTED, "last_error": None, "connected_at": datetime.now(UTC)}
        if error is not None:
            logger.warning("slack_agent_connection_error", error=error)
            values = {"status": SlackAgentStatus.ERROR, "last_error": error[:2000]}
        async with async_session() as session:
            # Only the status columns: the panel may be saving other fields at the same time.
            await session.execute(
                update(SlackAgent).where(SlackAgent.id == 1, SlackAgent.enabled.is_(True)).values(**values)
            )
            await session.commit()


def _fingerprint(row: SlackAgent | None, bot_token: str | None, app_token: str | None) -> str:
    parts = [bot_token or "", app_token or "", row.bot_user_id or "" if row else "", row.bot_name if row else ""]
    return hashlib.sha256("\n".join(parts).encode()).hexdigest()
