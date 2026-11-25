"""Tokens of the Slack agent, one encrypted JSON object on ``slack_agent.secrets_encrypted``."""

import time
from typing import TYPE_CHECKING

from app.services.secret_box import SecretsUnreadableError, decrypt_secrets, encrypt_secrets
from app.slack_agent import web_api

if TYPE_CHECKING:
    from app.models import SlackAgent

BOT_TOKEN = "bot_token"
APP_TOKEN = "app_token"
CLIENT_SECRET = "client_secret"
CONFIG_TOKEN = "config_token"
CONFIG_REFRESH_TOKEN = "config_refresh_token"
CONFIG_EXPIRES_AT = "config_token_expires_at"
# Slack's configuration tokens live 12 hours; rotate a little earlier.
CONFIG_TOKEN_TTL_SECONDS = 12 * 3600
ROTATE_MARGIN_SECONDS = 300


def read(row: SlackAgent | None) -> dict[str, str]:
    if row is None:
        return {}
    try:
        return decrypt_secrets(row.secrets_encrypted)
    except SecretsUnreadableError:
        return {}


def write(row: SlackAgent, values: dict[str, str]) -> None:
    row.secrets_encrypted = encrypt_secrets({key: value for key, value in values.items() if value})


def update(row: SlackAgent, **changes: str | None) -> None:
    values = read(row)
    for key, value in changes.items():
        if value:
            values[key] = value
        else:
            values.pop(key, None)
    write(row, values)


def set_config_tokens(row: SlackAgent, token: str, refresh: str | None, expires_at: int | None = None) -> None:
    update(
        row,
        **{
            CONFIG_TOKEN: token,
            CONFIG_REFRESH_TOKEN: refresh,
            CONFIG_EXPIRES_AT: str(expires_at or int(time.time()) + CONFIG_TOKEN_TTL_SECONDS),
        },
    )


async def config_token(row: SlackAgent) -> str | None:
    """A configuration token that works now: rotated with the refresh token when it is about to expire."""
    values = read(row)
    token = values.get(CONFIG_TOKEN)
    refresh = values.get(CONFIG_REFRESH_TOKEN)
    expires_at = int(values.get(CONFIG_EXPIRES_AT) or 0)
    if token and expires_at - ROTATE_MARGIN_SECONDS > time.time():
        return token
    if not refresh:
        return token  # maybe still valid; Slack says token_expired otherwise
    body = await web_api.call("tooling.tokens.rotate", None, data={"refresh_token": refresh})
    set_config_tokens(row, str(body["token"]), str(body.get("refresh_token") or refresh), _int(body.get("exp")))
    return str(body["token"])


def _int(value: object) -> int | None:
    try:
        return int(value)  # type: ignore[arg-type]
    except TypeError, ValueError:
        return None
