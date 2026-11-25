"""Abstraction over the workflow engine, so services and the API do not depend on Temporal.

``app.temporal.dispatcher.TemporalSyncDispatcher`` implements it. Tests
override the API dependency with a fake that records the calls.
"""

from typing import TYPE_CHECKING, Protocol

import structlog

if TYPE_CHECKING:
    import uuid

logger = structlog.get_logger()


class SyncDispatcher(Protocol):
    async def start_sync(self, connection_id: uuid.UUID, sync_run_id: uuid.UUID, *, force: bool) -> None:
        """Start ``SyncConnectionWorkflow`` for an existing ``sync_run``."""

    async def upsert_schedule(self, connection_id: uuid.UUID) -> None:
        """Create or update the periodic sync of the connection."""

    async def delete_schedule(self, connection_id: uuid.UUID) -> None:
        """Remove the periodic sync. No error when it does not exist."""


async def upsert_schedule_quietly(dispatcher: SyncDispatcher, connection_id: uuid.UUID) -> None:
    """Best effort: the worker reconciles schedules on startup, so a failure here is not fatal."""
    try:
        await dispatcher.upsert_schedule(connection_id)
    except Exception as exc:  # noqa: BLE001 - Temporal may be down; the worker fixes it on start
        logger.warning("sync_schedule_upsert_failed", connection_id=str(connection_id), error=str(exc))


async def delete_schedule_quietly(dispatcher: SyncDispatcher, connection_id: uuid.UUID) -> None:
    try:
        await dispatcher.delete_schedule(connection_id)
    except Exception as exc:  # noqa: BLE001 - the worker removes orphan schedules on start
        logger.warning("sync_schedule_delete_failed", connection_id=str(connection_id), error=str(exc))
