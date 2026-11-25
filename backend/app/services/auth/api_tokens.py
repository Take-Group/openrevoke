"""Personal API tokens: ``orv_`` plus 32 random bytes, only the SHA-256 is stored.

A token acts as its owner for the REST API (``Authorization: Bearer``) and the MCP server
(``app/mcp/``): the owner's role decides what it reaches, a ``read`` token only reads. Tokens are
managed with a panel session only (``app/api/api_tokens.py``), never with a token.
"""

import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

from sqlalchemy import select

from app.models import ApiToken, User
from app.models.enums import ApiTokenScope, UserStatus
from app.services import audit
from app.services.errors import NotFoundError

if TYPE_CHECKING:
    import uuid

    from sqlalchemy.ext.asyncio import AsyncSession

TOKEN_PREFIX = "orv_"
SHOWN_PREFIX_LENGTH = 10  # "orv_" and 6 random characters
# last_used_at is written at most this often, not on every request.
TOUCH_INTERVAL = timedelta(minutes=5)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def looks_like_token(value: str) -> bool:
    return value.startswith(TOKEN_PREFIX)


async def list_for_user(session: AsyncSession, user: User) -> list[ApiToken]:
    rows = await session.scalars(
        select(ApiToken).where(ApiToken.user_id == user.id).order_by(ApiToken.created_at.desc())
    )
    return list(rows)


async def create(
    session: AsyncSession, user: User, *, name: str, scope: ApiTokenScope, token: str | None = None
) -> tuple[ApiToken, str]:
    """New token for ``user``. Returns the row and the token, which is never shown again.

    ``token`` is for the development seed only (a fixed value that survives a reset).
    """
    token = token or TOKEN_PREFIX + secrets.token_urlsafe(32)
    row = ApiToken(
        user_id=user.id,
        name=name.strip(),
        token_hash=hash_token(token),
        prefix=token[:SHOWN_PREFIX_LENGTH],
        scope=scope,
    )
    session.add(row)
    await session.flush()
    await audit.record(session, "api_token.created", "api_token", row.id, {"name": row.name, "scope": scope})
    return row, token


async def revoke(session: AsyncSession, user: User, token_id: uuid.UUID) -> None:
    row = await session.get(ApiToken, token_id)
    if row is None or row.user_id != user.id:
        raise NotFoundError("API token not found.")
    await audit.record(session, "api_token.revoked", "api_token", row.id, {"name": row.name})
    await session.delete(row)


async def authenticate(session: AsyncSession, token: str | None) -> ApiToken | None:
    """The live token with its owner, or None. A pending owner cannot use it. Touches ``last_used_at``."""
    if not token or not looks_like_token(token):
        return None
    row = await session.scalar(select(ApiToken).where(ApiToken.token_hash == hash_token(token)))
    if row is None or row.user.status != UserStatus.ACTIVE:
        return None
    now = datetime.now(UTC)
    if row.last_used_at is None or now - row.last_used_at > TOUCH_INTERVAL:
        row.last_used_at = now
    return row


def actor_name(row: ApiToken) -> str:
    """How the audit log names a change made with the token."""
    return f"{row.user.email} (API token: {row.name})"
