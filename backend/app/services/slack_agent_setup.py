"""Setup of the Slack agent from the panel: create the app, set its icon, install it, save the tokens.

Slack cannot do everything by API. ``apps.manifest.create`` needs an app
configuration token (12 h, from api.slack.com/apps) and gives no app-level
token, so the admin still creates the ``xapp-`` token for Socket Mode by hand.
The bot token comes from OAuth when the panel has an https address, otherwise
the admin pastes it after "Install to Workspace".
"""

import json
import secrets
from datetime import UTC, datetime
from typing import TYPE_CHECKING
from urllib.parse import quote, urlencode

import structlog

from app.models import SlackAgent
from app.models.enums import SlackAgentStatus
from app.redis import redis_client
from app.schemas.slack_agent import SlackAgentOut, SlackAgentUpdate, SlackAppCreate, SlackTokensUpdate
from app.services import audit
from app.services import slack_agent_secrets as tokens
from app.services.ai_settings import get_row as get_ai_settings
from app.services.errors import ConflictError, InvalidInputError
from app.slack_agent import avatar, web_api
from app.slack_agent.manifest import BOT_SCOPES, build_manifest, oauth_redirect_url
from app.slack_agent.web_api import SlackApiError

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = structlog.get_logger()
OAUTH_STATE_KEY = "open-revoke:slack-agent:oauth-state:{state}"
OAUTH_STATE_TTL_SECONDS = 600
APP_PAGE = "https://api.slack.com/apps/{app_id}"
DEFAULT_BOT_NAME = "Open Revoke"


async def get_row(session: AsyncSession) -> SlackAgent | None:
    return await session.get(SlackAgent, 1)


async def state(session: AsyncSession) -> SlackAgentOut:
    row = await get_row(session)
    values = tokens.read(row)
    app_id = row.app_id if row else None
    return SlackAgentOut(
        status=row.status if row else SlackAgentStatus.NOT_CONFIGURED,
        enabled=row.enabled if row else False,
        bot_name=row.bot_name if row else None,
        app_id=app_id,
        team_name=row.team_name if row else None,
        bot_user_id=row.bot_user_id if row else None,
        has_bot_token=tokens.BOT_TOKEN in values,
        has_app_token=tokens.APP_TOKEN in values,
        has_config_token=tokens.CONFIG_TOKEN in values,
        avatar_set_at=row.avatar_set_at if row else None,
        avatar_error=row.avatar_error if row else None,
        last_error=row.last_error if row else None,
        connected_at=row.connected_at if row else None,
        ai_configured=await get_ai_settings(session) is not None,
        install_url=_install_url(row, values),
        oauth_install=bool(app_id and row and row.client_id and oauth_redirect_url()),
        app_settings_url=APP_PAGE.format(app_id=app_id) if app_id else None,
        app_token_url=f"{APP_PAGE.format(app_id=app_id)}/general" if app_id else None,
        manifest_url="https://api.slack.com/apps?new_app=1&manifest_json="
        + quote(json.dumps(build_manifest(row.bot_name if row else DEFAULT_BOT_NAME))),
    )


async def create_app(session: AsyncSession, data: SlackAppCreate) -> SlackAgentOut:
    """Create the Slack app from the manifest with a configuration token, then set its icon."""
    row = await get_row(session)
    if row is not None and row.app_id:
        raise ConflictError("A Slack app is already set up. Remove it in Open Revoke first")
    config_token = data.config_token.get_secret_value().strip()
    refresh = data.config_refresh_token.get_secret_value().strip() if data.config_refresh_token else None
    try:
        body = await web_api.call(
            "apps.manifest.create", config_token, data={"manifest": json.dumps(build_manifest(data.bot_name))}
        )
    except SlackApiError as exc:
        raise InvalidInputError(_setup_error(exc)) from exc
    credentials = body.get("credentials") or {}
    if row is None:
        row = SlackAgent(id=1, bot_name=data.bot_name)
        session.add(row)
    row.bot_name = data.bot_name
    row.app_id = str(body["app_id"])
    row.client_id = credentials.get("client_id")
    row.enabled = True
    row.status = SlackAgentStatus.NOT_CONFIGURED
    tokens.write(row, {tokens.CLIENT_SECRET: str(credentials.get("client_secret") or "")})
    tokens.set_config_tokens(row, config_token, refresh)
    await session.flush()
    await audit.record(session, "slack_agent.app_created", "slack_agent", None, {"app_id": row.app_id})
    await _set_icon(session, row, avatar.default_avatar(), "image/png")
    return await state(session)


async def set_avatar(session: AsyncSession, image: bytes | None, content_type: str | None) -> SlackAgentOut:
    """Upload ``image`` (or the default icon) as the app icon. Needs the configuration token."""
    row = await _require_app(session)
    if image is None:
        image, content_type = avatar.default_avatar(), "image/png"
    elif len(image) > avatar.MAX_BYTES:
        raise InvalidInputError("The image is larger than 5 MB")
    else:
        content_type = avatar.image_type(image)
        if content_type is None:
            raise InvalidInputError("Upload a PNG or JPEG image")
    if tokens.CONFIG_TOKEN not in tokens.read(row):
        raise InvalidInputError("Changing the icon needs an app configuration token. Enter it again")
    await _set_icon(session, row, image, content_type)
    if row.avatar_error:
        raise InvalidInputError(row.avatar_error)
    return await state(session)


async def start_oauth(session: AsyncSession) -> str:
    row = await _require_app(session)
    redirect = oauth_redirect_url()
    if not redirect or not row.client_id:
        raise InvalidInputError("Install from the Slack app page and paste the bot token: the panel is not on https")
    oauth_state = secrets.token_urlsafe(24)
    await redis_client.set(OAUTH_STATE_KEY.format(state=oauth_state), "1", ex=OAUTH_STATE_TTL_SECONDS)
    query = {"client_id": row.client_id, "scope": ",".join(BOT_SCOPES), "redirect_uri": redirect, "state": oauth_state}
    return f"https://slack.com/oauth/v2/authorize?{urlencode(query)}"


async def finish_oauth(session: AsyncSession, code: str, oauth_state: str) -> None:
    """Exchange the code from Slack's redirect for the bot token. The state proves the panel started it."""
    if not await redis_client.getdel(OAUTH_STATE_KEY.format(state=oauth_state)):
        raise InvalidInputError("The Slack sign-in link expired. Start the installation again")
    row = await _require_app(session)
    values = tokens.read(row)
    try:
        body = await web_api.call(
            "oauth.v2.access",
            None,
            data={
                "client_id": row.client_id or "",
                "client_secret": values.get(tokens.CLIENT_SECRET, ""),
                "code": code,
                "redirect_uri": oauth_redirect_url() or "",
            },
        )
    except SlackApiError as exc:
        raise InvalidInputError(_setup_error(exc)) from exc
    await _save_bot_token(session, row, str(body["access_token"]))
    if row.avatar_set_at is None and tokens.CONFIG_TOKEN in values:
        await _set_icon(
            session, row, avatar.default_avatar(), "image/png"
        )  # Slack may ignore an icon set before install


async def save_tokens(session: AsyncSession, data: SlackTokensUpdate) -> SlackAgentOut:
    """Paste the bot token and the app-level token. Each is checked with Slack before it is saved."""
    row = await get_row(session)
    if row is None:
        row = SlackAgent(id=1, bot_name=DEFAULT_BOT_NAME, enabled=True)
        session.add(row)
        await session.flush()
    if data.bot_token is not None:
        bot_token = data.bot_token.get_secret_value().strip()
        if not bot_token.startswith("xoxb-"):
            raise InvalidInputError("The bot token starts with xoxb-. Copy the Bot User OAuth Token")
        await _save_bot_token(session, row, bot_token)
    if data.app_token is not None:
        app_token = data.app_token.get_secret_value().strip()
        if not app_token.startswith("xapp-"):
            raise InvalidInputError(
                "The app-level token starts with xapp-. Create one with the connections:write scope"
            )
        try:
            await web_api.call("apps.connections.open", app_token)
        except SlackApiError as exc:
            raise InvalidInputError(_setup_error(exc)) from exc
        tokens.update(row, **{tokens.APP_TOKEN: app_token})
        await audit.record(session, "slack_agent.app_token_set", "slack_agent", None)
    _reset_connection(row)
    await session.flush()
    return await state(session)


async def update(session: AsyncSession, data: SlackAgentUpdate) -> SlackAgentOut:
    row = await get_row(session)
    if row is None:
        raise InvalidInputError("Set up the Slack app first")
    if row.enabled != data.enabled:
        row.enabled = data.enabled
        _reset_connection(row)
        await session.flush()
        await audit.record(session, "slack_agent.updated", "slack_agent", None, {"enabled": data.enabled})
    return await state(session)


async def remove(session: AsyncSession) -> None:
    """Forget the app and its tokens. The app stays in Slack; the admin deletes it at api.slack.com/apps."""
    row = await get_row(session)
    if row is None:
        return
    app_id = row.app_id
    await session.delete(row)
    await session.flush()
    await audit.record(session, "slack_agent.removed", "slack_agent", None, {"app_id": app_id})


async def _save_bot_token(session: AsyncSession, row: SlackAgent, bot_token: str) -> None:
    try:
        body = await web_api.call("auth.test", bot_token)
    except SlackApiError as exc:
        raise InvalidInputError(_setup_error(exc)) from exc
    if not body.get("bot_id"):
        raise InvalidInputError("This is not a bot token. Copy the Bot User OAuth Token (xoxb-…)")
    row.team_id = body.get("team_id")
    row.team_name = body.get("team")
    row.bot_user_id = body.get("user_id")
    if body.get("app_id") and not row.app_id:
        row.app_id = str(body["app_id"])
    tokens.update(row, **{tokens.BOT_TOKEN: bot_token})
    _reset_connection(row)
    await session.flush()
    await audit.record(session, "slack_agent.installed", "slack_agent", None, {"team": row.team_name})


async def _set_icon(session: AsyncSession, row: SlackAgent, image: bytes, content_type: str) -> None:
    """Best effort: a failed icon leaves the app working with Slack's default avatar."""
    try:
        token = await tokens.config_token(row)
        await web_api.call(
            "apps.icon.set",
            token,
            data={"app_id": row.app_id or ""},
            files={"file": ("icon.png" if content_type == "image/png" else "icon.jpg", image, content_type)},
        )
    except SlackApiError as exc:
        logger.warning("slack_agent_icon_failed", error=str(exc))
        row.avatar_error = _setup_error(exc)
    else:
        row.avatar_set_at = datetime.now(UTC)
        row.avatar_error = None
        await audit.record(session, "slack_agent.icon_set", "slack_agent", None)
    await session.flush()


async def _require_app(session: AsyncSession) -> SlackAgent:
    row = await get_row(session)
    if row is None or not row.app_id:
        raise InvalidInputError("Create the Slack app first")
    return row


def _reset_connection(row: SlackAgent) -> None:
    """The runner reconnects with the new tokens; until then the panel shows the new state."""
    values = tokens.read(row)
    ready = tokens.BOT_TOKEN in values and tokens.APP_TOKEN in values
    if not ready:
        row.status = SlackAgentStatus.NOT_CONFIGURED
    elif not row.enabled:
        row.status = SlackAgentStatus.DISABLED
    else:
        row.status = SlackAgentStatus.CONNECTING
    row.last_error = None


def _install_url(row: SlackAgent | None, values: dict[str, str]) -> str | None:
    if row is None or not row.app_id:
        return None
    if row.client_id and oauth_redirect_url():
        return "/api/slack-agent/oauth/start"
    return f"{APP_PAGE.format(app_id=row.app_id)}/install-on-team"


SETUP_ERRORS = {
    "invalid_auth": "Slack rejected the token. Check that you copied all of it",
    "not_authed": "Slack got no token",
    "token_expired": "The token expired. App configuration tokens last 12 hours: generate a new one",
    "token_revoked": "The token was revoked. Generate a new one",
    "not_allowed_token_type": "Wrong token type for this step",
    "invalid_manifest": "Slack rejected the app manifest",
    "invalid_icon_size": "The icon must be between 512x512 and 2000x2000 pixels",
    "error_bad_format": "Slack could not read the image",
    "bad_redirect_uri": "Slack does not accept the panel's address as the OAuth redirect URL",
    "invalid_code": "The Slack sign-in code expired. Start the installation again",
    "missing_scope": "The token lacks a scope",
}


def _setup_error(exc: SlackApiError) -> str:
    message = SETUP_ERRORS.get(exc.error, f"Slack {exc.method} failed: {exc.error}")
    return f"{message} ({exc.detail})" if exc.detail else message
