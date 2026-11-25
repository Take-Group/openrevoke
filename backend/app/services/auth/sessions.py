"""Panel sessions: a random token in an HttpOnly cookie, its SHA-256 in ``user_session``."""

import hashlib
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

from sqlalchemy import delete, select

from app.config import settings
from app.models import User, UserSession

if TYPE_CHECKING:
    import uuid

    from sqlalchemy.ext.asyncio import AsyncSession

COOKIE_NAME = "open_revoke_session"
# last_seen_at is written at most this often, not on every request.
TOUCH_INTERVAL = timedelta(minutes=5)


@dataclass(frozen=True)
class NewSession:
    row: UserSession
    token: str


def _hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def lifetime() -> timedelta:
    return timedelta(hours=settings.session_ttl_hours)


async def create(session: AsyncSession, user: User, *, user_agent: str | None) -> NewSession:
    token = secrets.token_urlsafe(32)
    now = datetime.now(UTC)
    row = UserSession(
        user_id=user.id,
        token_hash=_hash(token),
        expires_at=now + lifetime(),
        last_seen_at=now,
        user_agent=(user_agent or "")[:300] or None,
    )
    session.add(row)
    await session.flush()
    return NewSession(row=row, token=token)


async def find(session: AsyncSession, token: str | None) -> UserSession | None:
    """The live session for the cookie value, with its user. Touches ``last_seen_at``."""
    if not token:
        return None
    now = datetime.now(UTC)
    row = await session.scalar(
        select(UserSession).where(UserSession.token_hash == _hash(token), UserSession.expires_at > now)
    )
    if row is not None and now - row.last_seen_at > TOUCH_INTERVAL:
        row.last_seen_at = now
    return row


async def revoke(session: AsyncSession, session_id: uuid.UUID) -> None:
    await session.execute(delete(UserSession).where(UserSession.id == session_id))


async def revoke_all(session: AsyncSession, user_id: uuid.UUID, *, except_id: uuid.UUID | None = None) -> None:
    query = delete(UserSession).where(UserSession.user_id == user_id)
    if except_id is not None:
        query = query.where(UserSession.id != except_id)
    await session.execute(query)
