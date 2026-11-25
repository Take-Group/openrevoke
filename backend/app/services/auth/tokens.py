"""One-time links (invites, password resets) an admin passes on. The link carries the token, the table its SHA-256."""

import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

from sqlalchemy import select, update

from app.models import UserToken

if TYPE_CHECKING:
    import uuid

    from sqlalchemy.ext.asyncio import AsyncSession

    from app.models.enums import UserRole, UserTokenKind


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def now() -> datetime:
    return datetime.now(UTC)


async def create(
    session: AsyncSession,
    kind: UserTokenKind,
    *,
    email: str,
    ttl: timedelta,
    user_id: uuid.UUID | None = None,
    role: UserRole | None = None,
    created_by_id: uuid.UUID | None = None,
) -> tuple[UserToken, str]:
    """New token row and the plain token for the link (shown once, never stored)."""
    token = secrets.token_urlsafe(32)
    row = UserToken(
        kind=kind,
        token_hash=hash_token(token),
        email=email,
        user_id=user_id,
        role=role,
        created_by_id=created_by_id,
        expires_at=now() + ttl,
    )
    session.add(row)
    await session.flush()
    await session.refresh(row)  # created_at comes from the database
    return row, token


async def find_valid(session: AsyncSession, kind: UserTokenKind, token: str) -> UserToken | None:
    return await session.scalar(
        select(UserToken).where(
            UserToken.kind == kind,
            UserToken.token_hash == hash_token(token),
            UserToken.used_at.is_(None),
            UserToken.expires_at > now(),
        )
    )


async def consume(session: AsyncSession, kind: UserTokenKind, token: str) -> UserToken | None:
    """Mark the token used, atomically. None when it is unknown, expired or used already."""
    used_id = await session.scalar(
        update(UserToken)
        .where(
            UserToken.kind == kind,
            UserToken.token_hash == hash_token(token),
            UserToken.used_at.is_(None),
            UserToken.expires_at > now(),
        )
        .values(used_at=now())
        .returning(UserToken.id)
    )
    return await session.get(UserToken, used_id) if used_id else None


async def revoke_open(session: AsyncSession, kind: UserTokenKind, *, user_id: uuid.UUID) -> None:
    """Close every unused token of this kind for the user (e.g. older reset links)."""
    await session.execute(
        update(UserToken)
        .where(UserToken.kind == kind, UserToken.user_id == user_id, UserToken.used_at.is_(None))
        .values(used_at=now())
    )
