"""Attempt counters in Redis: sign-in, sign-up and turning 2FA off."""

import hashlib

from app.redis import redis_client
from app.services.errors import RateLimitedError

PREFIX = "open-revoke:auth:rate"


def _key(scope: str, subject: str) -> str:
    return f"{PREFIX}:{scope}:{hashlib.sha256(subject.lower().encode()).hexdigest()}"


async def hit(scope: str, subject: str, *, limit: int, window_seconds: int) -> bool:
    """Count one attempt. False when the subject is over the limit in the current window."""
    key = _key(scope, subject)
    count = await redis_client.incr(key)
    if count == 1:
        await redis_client.expire(key, window_seconds)
    return count <= limit


async def check(scope: str, subject: str, *, limit: int) -> None:
    """Refuse when the subject is already over the limit, without counting this attempt."""
    count = await redis_client.get(_key(scope, subject))
    if count is not None and int(count) >= limit:
        ttl = await redis_client.ttl(_key(scope, subject))
        minutes = max(1, (ttl if ttl > 0 else 60) // 60)
        raise RateLimitedError(f"Too many attempts. Try again in {minutes} minutes.")


async def enforce(scope: str, subject: str, *, limit: int, window_seconds: int) -> None:
    if not await hit(scope, subject, limit=limit, window_seconds=window_seconds):
        minutes = max(1, window_seconds // 60)
        raise RateLimitedError(f"Too many attempts. Try again in {minutes} minutes.")


async def reset(scope: str, subject: str) -> None:
    await redis_client.delete(_key(scope, subject))
