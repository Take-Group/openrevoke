"""2FA (TOTP) in Settings: a signed-in user turns it on or off. Free (MIT); keys and passkeys go to ee/.

Turning it on is two calls: ``start`` makes a secret and keeps it in a ticket
(``tickets``, 10 minutes, 5 codes); ``enable`` saves it on the user only when
the first code from it is right. Turning it off needs a current code, so a
stolen session alone cannot remove it. A lost phone: an admin resets 2FA
(``users.reset_totp``).
"""

from typing import TYPE_CHECKING

from app.services import audit
from app.services.auth import rate_limit, tickets, totp
from app.services.errors import AuthenticationError, InvalidInputError
from app.services.secret_box import decrypt_value, encrypt_value

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from app.models import User

WRONG_CODE = "Wrong code. Check the time on your phone and try the newest code."
DISABLE_LIMIT = 5
DISABLE_WINDOW_SECONDS = 15 * 60


async def start(user: User) -> tuple[str, totp.Enrollment]:
    if user.totp_secret_encrypted is not None:
        raise InvalidInputError("Two-factor authentication is already on.")
    secret = totp.new_secret()
    return await tickets.issue(user.id, secret, purpose=tickets.SETTINGS), totp.enrollment(secret, user.email)


async def enable(session: AsyncSession, user: User, *, ticket: str, code: str) -> User:
    pending = await tickets.load(ticket, tickets.SETTINGS)
    if pending.user_id != user.id or pending.enroll_secret is None:
        raise AuthenticationError(tickets.EXPIRED)
    if user.totp_secret_encrypted is not None:
        raise InvalidInputError("Two-factor authentication is already on.")
    step = totp.matching_step(pending.enroll_secret, code, after_step=None)
    if step is None:
        raise AuthenticationError(WRONG_CODE)
    await tickets.use(ticket)
    user.totp_secret_encrypted = encrypt_value(pending.enroll_secret)
    user.totp_last_step = step
    await audit.record(session, "user.totp_enabled", "user", user.id)
    return user


async def disable(session: AsyncSession, user: User, *, code: str) -> User:
    if user.totp_secret_encrypted is None:
        raise InvalidInputError("Two-factor authentication is already off.")
    await rate_limit.enforce("totp-disable", user.email, limit=DISABLE_LIMIT, window_seconds=DISABLE_WINDOW_SECONDS)
    step = totp.matching_step(decrypt_value(user.totp_secret_encrypted), code, after_step=user.totp_last_step)
    if step is None:
        raise AuthenticationError(WRONG_CODE)
    user.totp_secret_encrypted = None
    user.totp_last_step = None
    await audit.record(session, "user.totp_disabled", "user", user.id)
    return user
