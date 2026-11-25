"""Anonymous telemetry: one event when the first admin finishes the setup (``TELEMETRY.md``).

``POST {OPEN_REVOKE_TELEMETRY_URL}`` with the event name and the version, nothing else: no
e-mail, no organization name, no host, no identifier. Release builds only (the local stack
runs ``dev``); ``OPEN_REVOKE_TELEMETRY=false`` turns it off. A failure is logged and ignored.
"""

import httpx
import structlog

from app.config import settings
from app.services.update_check import parse_version

logger = structlog.get_logger()

SETUP_COMPLETED = "setup_completed"
TIMEOUT_SECONDS = 5


def enabled() -> bool:
    return settings.telemetry and parse_version(settings.version) is not None


def payload(event: str) -> dict[str, str]:
    return {"event": event, "version": settings.version}


async def post(event: str) -> int | None:
    """Send the event; the HTTP status, or None when the server was not reached."""
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT_SECONDS) as client:
            response = await client.post(
                settings.telemetry_url,
                json=payload(event),
                headers={"User-Agent": f"open-revoke/{settings.version}"},
            )
    except httpx.HTTPError as exc:
        logger.info("telemetry_unreachable", telemetry_event=event, error=str(exc))
        return None
    if response.status_code >= 300:
        logger.info("telemetry_not_accepted", telemetry_event=event, status=response.status_code)
    return response.status_code


async def report(event: str) -> None:
    """Background task of an endpoint: send the event when telemetry is on."""
    if enabled():
        await post(event)
