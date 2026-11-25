"""One sync or action at a time per connection: a lock in Redis."""

from contextlib import asynccontextmanager, suppress
from typing import TYPE_CHECKING

from redis.exceptions import LockError

from app.redis import redis_client

if TYPE_CHECKING:
    import uuid
    from collections.abc import AsyncIterator

# Longer than the sync activity timeout, so a live sync never loses its lock.
LOCK_TTL_SECONDS = 60 * 60


class ConnectionBusyError(Exception):
    def __init__(self) -> None:
        super().__init__("Another sync or action is running on this connection")


def lock_key(connection_id: uuid.UUID) -> str:
    return f"open-revoke:connection-lock:{connection_id}"


async def is_locked(connection_id: uuid.UUID) -> bool:
    return bool(await redis_client.exists(lock_key(connection_id)))


@asynccontextmanager
async def connection_lock(connection_id: uuid.UUID, *, wait_seconds: float | None = None) -> AsyncIterator[None]:
    """Hold the lock for the block. Raises ``ConnectionBusyError`` when it is taken.

    Without ``wait_seconds`` (sync) it gives up at once. Actions wait up to
    ``wait_seconds``, so the actions of one batch on one connection run one after another.
    """
    if wait_seconds is None:
        lock = redis_client.lock(lock_key(connection_id), timeout=LOCK_TTL_SECONDS, blocking=False)
    else:
        lock = redis_client.lock(
            lock_key(connection_id), timeout=LOCK_TTL_SECONDS, sleep=0.2, blocking_timeout=wait_seconds
        )
    if not await lock.acquire():
        raise ConnectionBusyError
    try:
        yield
    finally:
        # Releases only our own token; an expired lock someone else took stays theirs.
        with suppress(LockError):
            await lock.release()
