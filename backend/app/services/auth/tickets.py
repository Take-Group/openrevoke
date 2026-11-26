"""Second sign-in step. After the password the browser gets a short-lived ticket, not a session.

The ticket is exchanged for a session with a TOTP code. For a user without
2FA the ticket also carries a new TOTP secret (encrypted), saved on the user
only when the first code from it is correct.
"""

import hashlib
import secrets
import uuid
from dataclasses import dataclass

from app.redis import redis_client
from app.services.errors import AuthenticationError
from app.services.secret_box import decrypt_value, encrypt_value

PREFIX = "open-revoke:auth:ticket"
TTL_SECONDS = 600
MAX_ATTEMPTS = 5
EXPIRED = "The sign-in step expired. Sign in again."


# What a ticket was issued for. Each step accepts only its own purposes, so a Settings enrollment
# ticket cannot skip 2FA at sign-in and a sign-in ticket cannot enroll a new secret in Settings.
SIGN_IN = "sign_in"
SETUP = "setup"
SETTINGS = "settings"


@dataclass(frozen=True)
class Ticket:
    user_id: uuid.UUID
    enroll_secret: str | None  # set when the user enrolls 2FA in this step
    purpose: str


def _key(ticket: str) -> str:
    return f"{PREFIX}:{hashlib.sha256(ticket.encode()).hexdigest()}"


async def issue(user_id: uuid.UUID, enroll_secret: str | None = None, *, purpose: str = SIGN_IN) -> str:
    ticket = secrets.token_urlsafe(32)
    fields = {"user_id": str(user_id), "attempts": "0", "purpose": purpose}
    if enroll_secret:
        fields["enroll_secret"] = encrypt_value(enroll_secret).decode()
    key = _key(ticket)
    await redis_client.hset(key, mapping=fields)
    await redis_client.expire(key, TTL_SECONDS)
    return ticket


async def load(ticket: str, *purposes: str) -> Ticket:
    """Read the ticket and count one attempt. Raises when it is unknown, expired, used up or for another step."""
    key = _key(ticket)
    data = await redis_client.hgetall(key)
    if not data or data.get("purpose", SIGN_IN) not in purposes:
        raise AuthenticationError(EXPIRED)
    attempts = await redis_client.hincrby(key, "attempts", 1)
    if attempts > MAX_ATTEMPTS:
        await redis_client.delete(key)
        raise AuthenticationError("Too many wrong codes. Sign in again.")
    secret = data.get("enroll_secret")
    return Ticket(
        user_id=uuid.UUID(data["user_id"]),
        enroll_secret=decrypt_value(secret.encode()) if secret else None,
        purpose=data.get("purpose", SIGN_IN),
    )


async def discard(ticket: str) -> None:
    await redis_client.delete(_key(ticket))


async def use(ticket: str) -> None:
    """Spend the ticket once. Of two requests with the same ticket and code, only the first gets on."""
    if not await redis_client.delete(_key(ticket)):
        raise AuthenticationError(EXPIRED)
