"""Self sign-up: a person creates an account on /signup. The panel sends no e-mail.

The organization decides (``registration_*`` on ``Organization``): sign-up on or off, and whether
an e-mail in one of the listed domains gets in at once. Everyone else waits for an admin, who
approves in Settings -> Users. Nothing proves that the person owns the e-mail they typed: the
panel is meant to run inside the company, and the admin who approves knows their people.
Accounts made here always get the ``user`` role; an admin can promote them later.
"""

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import select

from app.models import Organization, User
from app.models.enums import UserRole, UserStatus
from app.services import audit
from app.services.auth import passwords, rate_limit
from app.services.auth.actor import current_actor
from app.services.errors import ConflictError, PermissionDeniedError

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

SIGNUP_LIMIT = 5
SIGNUP_WINDOW_SECONDS = 60 * 60
CLOSED = "Sign-up is closed. Ask an admin of your organization for an invite."
TAKEN = "An account with this e-mail already exists. Sign in, or ask an admin for a password reset link."
PENDING = "An admin has to approve your account first. Ask them, then sign in."


def email_domain(email: str) -> str:
    return email.rpartition("@")[2].lower()


def auto_approves(organization: Organization, email: str) -> bool:
    return organization.registration_auto_approve and email_domain(email) in organization.registration_domains


async def sign_up(session: AsyncSession, *, name: str, email: str, password: str) -> User:
    """Create a ``user`` account: active at once when its domain is auto-approved, otherwise pending."""
    passwords.check_policy(password)
    organization = await session.get(Organization, 1)
    if organization is None or not organization.registration_enabled:
        raise PermissionDeniedError(CLOSED)
    await rate_limit.enforce("signup", email, limit=SIGNUP_LIMIT, window_seconds=SIGNUP_WINDOW_SECONDS)
    if await session.scalar(select(User.id).where(User.email == email)):
        raise ConflictError(TAKEN)
    approved = auto_approves(organization, email)
    user = User(
        email=email,
        name=name.strip(),
        role=UserRole.USER,
        status=UserStatus.ACTIVE if approved else UserStatus.PENDING,
        approved_at=datetime.now(UTC) if approved else None,
        password_hash=passwords.hash_password(password),
    )
    session.add(user)
    await session.flush()
    current_actor.set(email)
    await audit.record(session, "user.signed_up", "user", user.id, {"email": email, "status": user.status})
    if approved:
        await audit.record(session, "user.approved", "user", user.id, {"by": "domain", "domain": email_domain(email)})
    return user


def sign_in_blocker(user: User) -> str | None:
    """Why this account cannot sign in yet, or None. Shown only after a correct password."""
    return PENDING if user.status == UserStatus.PENDING else None
