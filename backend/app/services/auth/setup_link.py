"""Setup link: the first admin can be created only with a token printed on the server.

Without it, whoever opened a fresh instance first became its admin; on a public domain that
could be a stranger (skills/backend/releases.md). The API makes a new
token at every start while no user exists and prints the link in the container log;
``python -m app.cli setup-link`` makes a new one on demand. Only the SHA-256 is kept, in Redis:
the link is shown once. Redis has no volume, so a lost token means running ``setup-link`` again.
"""

import hashlib
import hmac
import secrets

import structlog

from app.config import settings
from app.redis import redis_client
from app.services.errors import PermissionDeniedError

logger = structlog.get_logger()

KEY = "open-revoke:auth:setup-token"
INVALID = (
    "This setup link is not valid. On the server, run `open-revoke setup-link` "
    "(or `docker compose exec app python -m app.cli setup-link`) for a new one."
)


def _hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def link_for(token: str) -> str:
    return f"{settings.public_url}/setup?token={token}"


async def issue() -> str:
    """A new token replaces the old one. Returns the full setup link."""
    token = secrets.token_urlsafe(32)
    await redis_client.set(KEY, _hash(token))
    return link_for(token)


async def is_valid(token: str | None) -> bool:
    if not token:
        return False
    stored = await redis_client.get(KEY)
    return stored is not None and hmac.compare_digest(stored, _hash(token))


async def require_valid(token: str | None) -> None:
    if not await is_valid(token):
        raise PermissionDeniedError(INVALID)


async def discard() -> None:
    await redis_client.delete(KEY)


async def announce() -> None:
    """At API start, while setup is open: a fresh link in the log, easy to spot."""
    link = await issue()
    logger.warning("Setup link: open it to create the first admin", setup_link=link)
    # A plain line too: `docker compose logs app | grep "Setup link"` finds it in any log format.
    print(f"\n  Open Revoke setup link: {link}\n", flush=True)
