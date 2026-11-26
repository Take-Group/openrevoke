"""Panel users, managed by admins: list, approve a sign-up, change role, reset 2FA, remove (also rejects)."""

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import select

from app.models import User
from app.models.enums import UserRole, UserStatus
from app.services import audit
from app.services.auth import sessions
from app.services.errors import InvalidInputError, NotFoundError

if TYPE_CHECKING:
    import uuid

    from sqlalchemy.ext.asyncio import AsyncSession


async def list_users(session: AsyncSession) -> list[User]:
    return list(await session.scalars(select(User).order_by(User.created_at)))


async def get(session: AsyncSession, user_id: uuid.UUID) -> User:
    user = await session.get(User, user_id)
    if user is None:
        raise NotFoundError("User not found.")
    return user


async def _admin_count(session: AsyncSession) -> int:
    """Admins, with their rows locked: two admins demoting each other at once cannot leave none."""
    return len(list(await session.scalars(select(User.id).where(User.role == UserRole.ADMIN).with_for_update())))


async def approve(session: AsyncSession, user_id: uuid.UUID, *, admin: User) -> User:
    """Let a sign-up in. Nothing is sent: tell them yourself that they can sign in."""
    user = await get(session, user_id)
    if user.status != UserStatus.PENDING:
        raise InvalidInputError("This account is already active.")
    user.status, user.approved_at = UserStatus.ACTIVE, datetime.now(UTC)
    await audit.record(session, "user.approved", "user", user.id, {"by": "admin"})
    return user


async def set_role(session: AsyncSession, user_id: uuid.UUID, role: UserRole, *, admin: User) -> User:
    user = await get(session, user_id)
    if user.role == role:
        return user
    if user.role == UserRole.ADMIN and await _admin_count(session) <= 1:
        raise InvalidInputError("The panel needs at least one admin.")
    previous, user.role = user.role, role
    await audit.record(session, "user.role_changed", "user", user.id, {"from": previous, "to": role})
    return user


async def reset_totp(session: AsyncSession, user_id: uuid.UUID, *, admin: User) -> User:
    """Lost phone: turn 2FA off and sign the user out. The next sign-in sets up a new authenticator."""
    user = await get(session, user_id)
    user.totp_secret_encrypted = None
    user.totp_last_step = None
    await sessions.revoke_all(session, user.id)
    await audit.record(session, "user.totp_reset", "user", user.id)
    return user


async def remove(session: AsyncSession, user_id: uuid.UUID, *, admin: User) -> None:
    user = await get(session, user_id)
    if user.id == admin.id:
        raise InvalidInputError("You cannot remove yourself.")
    if user.role == UserRole.ADMIN and await _admin_count(session) <= 1:
        raise InvalidInputError("The panel needs at least one admin.")
    await audit.record(session, "user.removed", "user", user.id, {"email": user.email})
    await session.delete(user)
    await session.flush()
