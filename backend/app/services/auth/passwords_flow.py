"""Password reset with a one-time link, and change while signed in. No e-mail.

A reset link reaches the person by hand: an admin creates it in the panel and passes it on
(``issue_link``), and an admin who forgot their own password runs
``python -m app.cli reset-link`` on the server.
"""

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

from app.config import settings
from app.models import User
from app.models.enums import UserStatus, UserTokenKind
from app.services import audit
from app.services.auth import passwords, rate_limit, sessions, tokens
from app.services.auth.actor import current_actor
from app.services.errors import AuthenticationError, InvalidInputError

if TYPE_CHECKING:
    import uuid

    from sqlalchemy.ext.asyncio import AsyncSession

LINK_TTL_HOURS = 24  # passed by hand (chat, phone), so a day rather than minutes
INVALID_LINK = "This reset link is invalid, used or expired. Ask an admin for a new one."


async def issue_link(session: AsyncSession, user: User, *, by: str) -> tuple[str, datetime]:
    """A one-time reset link to pass on by hand (admin in the panel, or the CLI). Older links stop working."""
    if user.status != UserStatus.ACTIVE:
        raise InvalidInputError("This account cannot sign in yet: approve it first.")
    await tokens.revoke_open(session, UserTokenKind.PASSWORD_RESET, user_id=user.id)
    row, token = await tokens.create(
        session, UserTokenKind.PASSWORD_RESET, email=user.email, user_id=user.id, ttl=timedelta(hours=LINK_TTL_HOURS)
    )
    await audit.record(session, "user.password_reset_link_created", "user", user.id, {"by": by})
    return f"{settings.public_url}/reset-password?token={token}", row.expires_at


async def reset(session: AsyncSession, *, token: str, password: str) -> None:
    """Set a new password with a link. Signs out every session; 2FA stays as it was."""
    passwords.check_policy(password)
    row = await tokens.consume(session, UserTokenKind.PASSWORD_RESET, token)
    user = await session.get(User, row.user_id) if row and row.user_id else None
    if user is None:
        raise InvalidInputError(INVALID_LINK)
    await _set_password(session, user, password, keep_session=None)
    await rate_limit.reset("login-account", user.email)


async def change(
    session: AsyncSession, user: User, *, current_password: str, new_password: str, session_id: uuid.UUID
) -> None:
    if not passwords.verify_password(user.password_hash, current_password):
        raise AuthenticationError("The current password is wrong.")
    passwords.check_policy(new_password)
    if current_password == new_password:
        raise InvalidInputError("The new password is the same as the current one.")
    await _set_password(session, user, new_password, keep_session=session_id)


async def _set_password(session: AsyncSession, user: User, password: str, *, keep_session: uuid.UUID | None) -> None:
    user.password_hash = passwords.hash_password(password)
    user.password_changed_at = datetime.now(UTC)
    await sessions.revoke_all(session, user.id, except_id=keep_session)
    await tokens.revoke_open(session, UserTokenKind.PASSWORD_RESET, user_id=user.id)
    current_actor.set(user.email)
    await audit.record(session, "user.password_changed", "user", user.id)
