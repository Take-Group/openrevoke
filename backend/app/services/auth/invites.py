"""Invites: an admin creates a one-time registration link and passes it on (the panel sends no e-mail)."""

from datetime import timedelta
from typing import TYPE_CHECKING

from sqlalchemy import select

from app.config import settings
from app.models import User, UserToken
from app.models.enums import UserRole, UserTokenKind
from app.services import audit
from app.services.auth import tokens
from app.services.errors import ConflictError, NotFoundError

if TYPE_CHECKING:
    import uuid

    from sqlalchemy.ext.asyncio import AsyncSession


async def list_open(session: AsyncSession) -> list[UserToken]:
    rows = await session.scalars(
        select(UserToken)
        .where(UserToken.kind == UserTokenKind.INVITE, UserToken.used_at.is_(None), UserToken.expires_at > tokens.now())
        .order_by(UserToken.created_at.desc())
    )
    return list(rows)


async def create(session: AsyncSession, *, email: str, role: UserRole, admin: User) -> tuple[UserToken, str]:
    """New invite. An older open invite for the same e-mail is closed. Returns the row and the link."""
    if await session.scalar(select(User.id).where(User.email == email)):
        raise ConflictError("A user with this e-mail already exists.")
    for old in await list_open(session):
        if old.email == email:
            old.used_at = tokens.now()
    hours = settings.invite_ttl_hours
    row, token = await tokens.create(
        session, UserTokenKind.INVITE, email=email, role=role, created_by_id=admin.id, ttl=timedelta(hours=hours)
    )
    await audit.record(session, "user.invited", "invite", row.id, {"email": email, "role": role})
    link = f"{settings.public_url}/register?token={token}"
    return row, link


async def revoke(session: AsyncSession, invite_id: uuid.UUID) -> None:
    row = await session.get(UserToken, invite_id)
    if row is None or row.kind != UserTokenKind.INVITE or row.used_at is not None:
        raise NotFoundError("Invite not found or already used.")
    row.used_at = tokens.now()
    await audit.record(session, "user.invite_revoked", "invite", row.id, {"email": row.email})
