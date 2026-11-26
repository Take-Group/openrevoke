"""Sign-in limits and the audit of failed sign-ins (services/auth/sign_in.py)."""

import uuid

import pytest
from sqlalchemy import select

from app.database import async_session
from app.models import AuditEvent, User
from app.models.enums import UserRole
from app.services.auth import passwords, sign_in
from app.services.errors import AuthenticationError, RateLimitedError

pytestmark = pytest.mark.integration

PASSWORD = "correct horse battery"


async def _user() -> str:
    email = f"limits-{uuid.uuid4().hex[:10]}@example.com"
    async with async_session() as session, session.begin():
        session.add(
            User(email=email, name="Limits", role=UserRole.USER, password_hash=passwords.hash_password(PASSWORD))
        )
    return email


async def _login(email: str, password: str, ip: str) -> None:
    async with async_session() as session, session.begin():
        await sign_in.login(session, email=email, password=password, user_agent="pytest", client_ip=ip)


async def test_wrong_passwords_from_one_address_do_not_lock_the_owner_out() -> None:
    email = await _user()
    attacker = f"198.51.100.{uuid.uuid4().int % 250}"
    for _ in range(sign_in.LOGIN_LIMIT):
        with pytest.raises(AuthenticationError):
            await _login(email, "wrong password!!", attacker)
    with pytest.raises(RateLimitedError):
        await _login(email, PASSWORD, attacker)
    # The owner, from another address, still signs in.
    await _login(email, PASSWORD, "203.0.113.200")


async def test_failed_sign_in_is_audited_with_the_address() -> None:
    email = await _user()
    with pytest.raises(AuthenticationError):
        await _login(email, "wrong password!!", "192.0.2.44")
    async with async_session() as session:
        event = await session.scalar(
            select(AuditEvent).where(AuditEvent.event == "user.sign_in_failed").order_by(AuditEvent.at.desc()).limit(1)
        )
    assert event is not None
    assert event.actor == "anonymous"
    assert event.data == {"email": email, "ip": "192.0.2.44", "reason": "password"}
