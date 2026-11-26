"""Security rules that need the database and Redis: 2FA tickets and limits, secrets bound to their URL,
roles a requester picks for themselves."""

import uuid

import pyotp
import pytest
from pydantic import SecretStr

from app.database import async_session
from app.models import App, Person, User
from app.models.enums import AiProvider, Integration, RequestPolicy, UserRole
from app.schemas.ai import AiSettingsUpdate
from app.schemas.connections import ConnectionUpsert
from app.services import ai_settings, connections
from app.services.access.outcomes import Outcome
from app.services.access.requests import NewRequest, request_access
from app.services.auth import passwords, sign_in, tickets, totp, two_factor
from app.services.errors import AuthenticationError, InvalidInputError, RateLimitedError
from app.services.secret_box import decrypt_secrets, encrypt_value

pytestmark = pytest.mark.integration

PASSWORD = "correct horse battery"


def _suffix() -> str:
    return uuid.uuid4().hex[:10]


async def _user_with_totp() -> tuple[User, str]:
    secret = totp.new_secret()
    async with async_session() as session, session.begin():
        user = User(
            email=f"totp-{_suffix()}@example.com",
            name="Totp",
            role=UserRole.USER,
            password_hash=passwords.hash_password(PASSWORD),
            totp_secret_encrypted=encrypt_value(secret),
        )
        session.add(user)
    return user, secret


async def _complete(ticket: str, code: str) -> None:
    async with async_session() as session, session.begin():
        await sign_in.complete(session, ticket=ticket, code=code, user_agent="pytest", client_ip="192.0.2.1")


async def test_wrong_codes_count_per_account_across_tickets() -> None:
    user, _ = await _user_with_totp()
    for _ in range(sign_in.TOTP_ACCOUNT_LIMIT // tickets.MAX_ATTEMPTS):
        ticket = await tickets.issue(user.id)  # a fresh ticket per correct password
        for _ in range(tickets.MAX_ATTEMPTS):
            with pytest.raises(AuthenticationError):
                await _complete(ticket, "000000")
    with pytest.raises(RateLimitedError):
        await _complete(await tickets.issue(user.id), "000000")


async def test_a_ticket_signs_in_once() -> None:
    user, secret = await _user_with_totp()
    ticket = await tickets.issue(user.id)
    await _complete(ticket, pyotp.TOTP(secret).now())
    with pytest.raises(AuthenticationError):
        await _complete(ticket, pyotp.TOTP(secret).now())


async def test_a_settings_ticket_cannot_skip_two_factor_at_sign_in() -> None:
    async with async_session() as session, session.begin():
        user = User(
            email=f"skip-{_suffix()}@example.com",
            name="Skip",
            role=UserRole.USER,
            password_hash=passwords.hash_password(PASSWORD),
        )
        session.add(user)
    ticket, _ = await two_factor.start(user)
    async with async_session() as session, session.begin():
        with pytest.raises(AuthenticationError):
            await sign_in.skip_enrollment(session, ticket=ticket, user_agent="pytest")


async def _scim_app() -> uuid.UUID:
    async with async_session() as session, session.begin():
        app = App(name=f"Scim {_suffix()}", slug=f"scim-{_suffix()}", integration=Integration.SCIM)
        session.add(app)
    return app.id


async def _save_scim(app_id: uuid.UUID, base_url: str, token: str | None) -> dict[str, str]:
    async with async_session() as session, session.begin():
        connection = await connections.upsert_connection(
            session,
            app_id,
            ConnectionUpsert(
                connector_key="scim",
                config={"base_url": base_url},
                secrets={"token": token} if token else None,
            ),
        )
        return decrypt_secrets(connection.secrets_encrypted)


async def test_a_stored_token_does_not_follow_a_new_url() -> None:
    app_id = await _scim_app()
    assert await _save_scim(app_id, "https://a.example/scim/v2", "token-a") == {"token": "token-a"}
    assert await _save_scim(app_id, "https://a.example/scim/v2", None) == {"token": "token-a"}  # same URL keeps it
    with pytest.raises(InvalidInputError):
        await _save_scim(app_id, "https://attacker.example/scim/v2", None)
    assert await _save_scim(app_id, "https://b.example/scim/v2", "token-b") == {"token": "token-b"}


async def test_the_saved_ai_key_does_not_follow_a_new_base_url() -> None:
    def update(base_url: str, key: str | None) -> AiSettingsUpdate:
        return AiSettingsUpdate(
            provider=AiProvider.CUSTOM,
            model="m",
            base_url=base_url,
            api_key=SecretStr(key) if key else None,
        )

    async with async_session() as session:
        await ai_settings.save(session, update("https://llm-a.example/v1", "key-a"))
        saved = await ai_settings.save(session, update("https://llm-a.example/v1", None))
        assert saved.api_key_set
        moved = await ai_settings.save(session, update("https://attacker.example/v1", None))
        assert not moved.api_key_set
        await session.rollback()  # leave the settings of the test database as they were


class _NoDispatch:
    async def start_action(self, action_id: uuid.UUID, *, retry: int = 0) -> None:
        raise AssertionError("no write should start in this test")


async def _ask(policy: RequestPolicy, role: str | None) -> Outcome:
    async with async_session() as session, session.begin():
        app = App(name=f"Auto {_suffix()}", slug=f"auto-{_suffix()}", request_policy=policy)
        person = Person(first_name="Req", last_name="Uester", primary_email=f"req-{_suffix()}@example.com")
        session.add_all([app, person])
        await session.flush()
        result = await request_access(
            session,
            person=person,
            app=app,
            new=NewRequest(justification="work", requested_by=person.primary_email, role=role),
            dispatcher=_NoDispatch(),
        )
        return result.outcome


async def test_automatic_policy_does_not_grant_a_role_the_requester_picked() -> None:
    assert await _ask(RequestPolicy.AUTOMATIC, None) == Outcome.WAITING_FOR_ADMIN  # approved; a manual task
    assert await _ask(RequestPolicy.AUTOMATIC, "admin") == Outcome.WAITING_FOR_APPROVAL
