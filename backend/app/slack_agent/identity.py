"""Who is writing: a Slack user as a person in Open Revoke, or as a panel admin.

A person is found by their Slack account (synced by the Slack connector, the
external id is the Slack user id), then by the e-mail of their Slack profile
matched to a primary e-mail or an alias. E-mails from Slack are cached in Redis.
"""

from typing import TYPE_CHECKING

from sqlalchemy import select

from app.models import Account, Connection, Person, User
from app.models.enums import AccountStatus, UserRole
from app.redis import redis_client
from app.services.matching import match_email, normalize_email
from app.slack_agent import web_api
from app.slack_agent.web_api import SlackApiError

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from app.slack_agent.runtime import SlackRuntime

EMAIL_KEY = "open-revoke:slack-agent:email:{user_id}"
USER_ID_KEY = "open-revoke:slack-agent:user-id:{email}"
CACHE_SECONDS = 3600
SLACK_CONNECTOR = "slack"


async def find_person(session: AsyncSession, rt: SlackRuntime, user_id: str) -> tuple[Person | None, str | None]:
    """The person and the e-mail of the Slack profile (``None`` when Slack has no e-mail)."""
    person_id = await session.scalar(
        select(Account.person_id)
        .join(Connection, Connection.id == Account.connection_id)
        .where(
            Connection.connector_key == SLACK_CONNECTOR,
            Account.external_id == user_id,
            Account.person_id.is_not(None),
            Account.status != AccountStatus.REMOVED,
        )
        .limit(1)
    )
    email = await slack_email(rt, user_id)
    if person_id is None:
        person_id = (await match_email(session, email)).person_id
    person = await session.get(Person, person_id) if person_id else None
    return person, email


async def find_admin(session: AsyncSession, rt: SlackRuntime, user_id: str) -> User | None:
    email = await slack_email(rt, user_id)
    if email is None:
        return None
    return await session.scalar(select(User).where(User.email == email, User.role == UserRole.ADMIN))


async def slack_email(rt: SlackRuntime, user_id: str) -> str | None:
    key = EMAIL_KEY.format(user_id=user_id)
    cached = await redis_client.get(key)
    if cached is not None:
        return cached or None
    body = await web_api.call("users.info", rt.bot_token, data={"user": user_id})
    profile = (body.get("user") or {}).get("profile") or {}
    email = normalize_email(profile.get("email")) or ""
    await redis_client.set(key, email, ex=CACHE_SECONDS)
    return email or None


async def slack_user_for_email(rt: SlackRuntime, email: str) -> str | None:
    key = USER_ID_KEY.format(email=email)
    cached = await redis_client.get(key)
    if cached is not None:
        return cached or None
    try:
        body = await web_api.call("users.lookupByEmail", rt.bot_token, data={"email": email})
        user_id = str((body.get("user") or {}).get("id") or "")
    except SlackApiError as exc:
        if exc.error != "users_not_found":
            raise
        user_id = ""
    await redis_client.set(key, user_id, ex=CACHE_SECONDS)
    return user_id or None
