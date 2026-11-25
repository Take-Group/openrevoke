"""Abstraction over the workflow engine for discovery scans (like ``app.services.sync_dispatch``).

``app.temporal.scan_dispatcher.TemporalScanDispatcher`` implements it. Tests
override the API dependency with a fake that records the calls.
"""

from typing import TYPE_CHECKING, Protocol

import structlog

if TYPE_CHECKING:
    import uuid

logger = structlog.get_logger()


class ScanDispatcher(Protocol):
    async def start_scan(self, connection_id: uuid.UUID, scan_run_id: uuid.UUID) -> None:
        """Start ``ScanConnectionWorkflow`` for an existing ``scan_run``."""

    async def upsert_scan_schedule(self, connection_id: uuid.UUID) -> None:
        """Create or update the periodic scan of the connection."""


async def upsert_scan_schedule_quietly(dispatcher: ScanDispatcher, connection_id: uuid.UUID) -> None:
    """Best effort: the worker reconciles schedules on startup, so a failure here is not fatal."""
    try:
        await dispatcher.upsert_scan_schedule(connection_id)
    except Exception as exc:  # noqa: BLE001 - Temporal may be down; the worker fixes it on start
        logger.warning("scan_schedule_upsert_failed", connection_id=str(connection_id), error=str(exc))
