"""First-run setup, sign-in with password and TOTP, registration by invite (self sign-up: ``signup``).

Sign-in and registration never offer 2FA: a user without
2FA gets a session right after the password; a user with 2FA gets a ticket
(``tickets``) that a correct TOTP code turns into a session. Only the first-run
setup offers the first admin to turn 2FA on, and they may skip it
(``skip_enrollment``). Everyone else turns it on in Settings (``two_factor``).
"""

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import func, select, text

from app.database import async_session
from app.models import Organization, User
from app.models.enums import UserRole, UserTokenKind
from app.services import audit
from app.services.auth import passwords, rate_limit, sessions, setup_link, signup, tickets, tokens, totp
from app.services.auth.actor import current_actor
from app.services.errors import AuthenticationError, ConflictError, NotFoundError, PermissionDeniedError
from app.services.secret_box import decrypt_value, encrypt_value

if TYPE_CHECKING:
    import uuid

    from sqlalchemy.ext.asyncio import AsyncSession

WRONG_CREDENTIALS = "Wrong e-mail or password."
WRONG_CODE = "Wrong code. Check the time on your phone and try the newest code."
# Any number: one advisory lock for the first-run setup, so two browsers cannot both create an admin.
SETUP_LOCK_ID = 7_412_001
# Sign-in attempts per 15 minutes: one e-mail from one address, one address for any e-mail, and
# wrong passwords for one e-mail from anywhere. The per-account limit counts only failures and is
# high, so a stranger who knows an e-mail cannot lock its owner out with a few wrong passwords.
LOGIN_LIMIT = 10
LOGIN_IP_LIMIT = 50
LOGIN_ACCOUNT_LIMIT = 100
# Wrong 2FA codes for one account per 15 minutes, over all its sign-in tickets.
TOTP_ACCOUNT_LIMIT = 10
LOGIN_WINDOW_SECONDS = 15 * 60


@dataclass(frozen=True)
class PendingStep:
    ticket: str
    enrollment: totp.Enrollment | None


@dataclass(frozen=True)
class SignedIn:
    user: User
    session_token: str


SignInResult = PendingStep | SignedIn


async def setup_required(session: AsyncSession) -> bool:
    return not await session.scalar(select(func.count()).select_from(User))


async def get_organization(session: AsyncSession) -> Organization | None:
    return await session.get(Organization, 1)


async def setup(
    session: AsyncSession,
    *,
    organization_name: str,
    currency: str,
    timezone: str,
    name: str,
    email: str,
    password: str,
    token: str,
) -> PendingStep:
    """Create the organization and its first user, an admin. Only while no user exists, with the setup token."""
    await setup_link.require_valid(token)
    passwords.check_policy(password)
    await session.execute(text("SELECT pg_advisory_xact_lock(:id)"), {"id": SETUP_LOCK_ID})
    if not await setup_required(session):
        raise ConflictError("The panel is already set up. Sign in instead.")
    organization = await get_organization(session)
    if organization is None:
        organization = Organization(id=1, name=organization_name, currency=currency, timezone=timezone)
        session.add(organization)
    else:
        organization.name, organization.currency, organization.timezone = organization_name, currency, timezone
    user = await _create_user(session, email=email, name=name, password=password, role=UserRole.ADMIN)
    await audit.record(
        session,
        "organization.created",
        "organization",
        None,
        {"name": organization_name, "currency": currency, "timezone": timezone},
    )
    await setup_link.discard()
    # The only place that offers 2FA: the first admin may turn it on now or skip it.
    secret = totp.new_secret()
    return PendingStep(
        ticket=await tickets.issue(user.id, secret, purpose=tickets.SETUP),
        enrollment=totp.enrollment(secret, user.email),
    )


async def login(
    session: AsyncSession, *, email: str, password: str, user_agent: str | None, client_ip: str
) -> SignInResult:
    window = LOGIN_WINDOW_SECONDS
    await rate_limit.enforce("login-ip", client_ip, limit=LOGIN_IP_LIMIT, window_seconds=window)
    await rate_limit.enforce("login", _login_subject(email, client_ip), limit=LOGIN_LIMIT, window_seconds=window)
    await rate_limit.check("login-account", email, limit=LOGIN_ACCOUNT_LIMIT)
    user = await session.scalar(select(User).where(User.email == email))
    if not passwords.verify_password(user.password_hash if user else None, password) or user is None:
        await rate_limit.hit("login-account", email, limit=LOGIN_ACCOUNT_LIMIT, window_seconds=window)
        await record_failed_sign_in(email, user.id if user else None, client_ip, "password")
        raise AuthenticationError(WRONG_CREDENTIALS)
    if blocker := signup.sign_in_blocker(user):
        raise PermissionDeniedError(blocker)
    return await _next_step(session, user, user_agent, client_ip)


async def record_failed_sign_in(email: str, user_id: uuid.UUID | None, client_ip: str, reason: str) -> None:
    """Audit a failed sign-in in its own transaction: the request's own one is rolled back."""
    token = current_actor.set("anonymous")
    try:
        async with async_session() as own, own.begin():
            await audit.record(
                own, "user.sign_in_failed", "user", user_id, {"email": email, "ip": client_ip, "reason": reason}
            )
    finally:
        current_actor.reset(token)


def _login_subject(email: str, client_ip: str) -> str:
    return f"{email}|{client_ip}"


async def complete(
    session: AsyncSession, *, ticket: str, code: str, user_agent: str | None, client_ip: str | None = None
) -> SignedIn:
    """Check the TOTP code of a ticket and open a session."""
    pending = await tickets.load(ticket, tickets.SIGN_IN, tickets.SETUP)
    user = await session.get(User, pending.user_id)
    if user is None:
        await tickets.discard(ticket)
        raise AuthenticationError(tickets.EXPIRED)
    if pending.enroll_secret is not None:
        secret = pending.enroll_secret
    elif user.totp_secret_encrypted is not None:
        secret = decrypt_value(user.totp_secret_encrypted)
    else:  # 2FA was reset after the ticket was issued
        await tickets.discard(ticket)
        raise AuthenticationError(tickets.EXPIRED)
    if pending.enroll_secret is not None and user.totp_secret_encrypted is not None:
        await tickets.discard(ticket)  # 2FA was turned on after this setup ticket: never replace that secret
        raise AuthenticationError(tickets.EXPIRED)
    # Wrong codes count per account across tickets: a new ticket per correct password is no new budget.
    await rate_limit.check("totp", user.email, limit=TOTP_ACCOUNT_LIMIT)
    step = totp.matching_step(secret, code, after_step=user.totp_last_step)
    if step is None:
        await rate_limit.hit("totp", user.email, limit=TOTP_ACCOUNT_LIMIT, window_seconds=LOGIN_WINDOW_SECONDS)
        await record_failed_sign_in(user.email, user.id, client_ip or "unknown", "totp")
        raise AuthenticationError(WRONG_CODE)
    await tickets.use(ticket)
    current_actor.set(user.email)
    if pending.enroll_secret is not None:
        user.totp_secret_encrypted = encrypt_value(secret)
        await audit.record(session, "user.totp_enabled", "user", user.id)
    user.totp_last_step = step
    return await _open_session(session, user, user_agent, client_ip)


async def skip_enrollment(session: AsyncSession, *, ticket: str, user_agent: str | None) -> SignedIn:
    """Open a session without 2FA. Only for the first-run setup ticket, which offers enrollment."""
    pending = await tickets.load(ticket, tickets.SETUP)
    user = await session.get(User, pending.user_id)
    if user is None:
        await tickets.discard(ticket)
        raise AuthenticationError(tickets.EXPIRED)
    if pending.enroll_secret is None or user.totp_secret_encrypted is not None:
        raise AuthenticationError("Two-factor authentication is on for this account. Enter the code.")
    await tickets.use(ticket)
    current_actor.set(user.email)
    await audit.record(session, "user.totp_skipped", "user", user.id)
    return await _open_session(session, user, user_agent)


async def _open_session(
    session: AsyncSession, user: User, user_agent: str | None, client_ip: str | None = None
) -> SignedIn:
    await rate_limit.reset("login-account", user.email)
    await rate_limit.reset("totp", user.email)
    if client_ip:
        await rate_limit.reset("login", _login_subject(user.email, client_ip))
    current_actor.set(user.email)
    user.last_login_at = datetime.now(UTC)
    new_session = await sessions.create(session, user, user_agent=user_agent)
    await audit.record(session, "user.signed_in", "user", user.id, {"ip": client_ip} if client_ip else None)
    return SignedIn(user=user, session_token=new_session.token)


async def invite_info(session: AsyncSession, token: str) -> tuple[str, Organization | None, datetime]:
    invite = await tokens.find_valid(session, UserTokenKind.INVITE, token)
    if invite is None:
        raise NotFoundError("This invite link is invalid, used or expired. Ask an admin for a new one.")
    return invite.email, await get_organization(session), invite.expires_at


async def register(session: AsyncSession, *, token: str, name: str, password: str, user_agent: str | None) -> SignedIn:
    passwords.check_policy(password)
    invite = await tokens.consume(session, UserTokenKind.INVITE, token)
    if invite is None:
        raise NotFoundError("This invite link is invalid, used or expired. Ask an admin for a new one.")
    if await session.scalar(select(User.id).where(User.email == invite.email)):
        raise ConflictError("A user with this e-mail already exists. Sign in instead.")
    user = await _create_user(
        session, email=invite.email, name=name, password=password, role=invite.role or UserRole.USER
    )
    invite.user_id = user.id
    return await _open_session(session, user, user_agent)


async def logout(session: AsyncSession, session_id: uuid.UUID, user: User) -> None:
    await sessions.revoke(session, session_id)
    await audit.record(session, "user.signed_out", "user", user.id)


async def _create_user(session: AsyncSession, *, email: str, name: str, password: str, role: UserRole) -> User:
    user = User(email=email, name=name.strip(), role=role, password_hash=passwords.hash_password(password))
    session.add(user)
    await session.flush()
    current_actor.set(email)
    await audit.record(session, "user.created", "user", user.id, {"email": email, "role": role})
    return user


async def _next_step(
    session: AsyncSession, user: User, user_agent: str | None, client_ip: str | None = None
) -> SignInResult:
    """With 2FA: a ticket for the code step. Without: the session right away."""
    if user.totp_secret_encrypted is not None:
        return PendingStep(ticket=await tickets.issue(user.id), enrollment=None)
    return await _open_session(session, user, user_agent, client_ip)
