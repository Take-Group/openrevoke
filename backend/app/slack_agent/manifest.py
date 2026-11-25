"""The Slack app manifest of the agent: a bot that reads and writes direct messages over Socket Mode."""

from typing import Any

from app.config import settings

BOT_SCOPES = ("chat:write", "im:history", "im:read", "im:write", "users:read", "users:read.email")
BOT_EVENTS = ("message.im",)
CALLBACK_PATH = "/api/slack-agent/oauth/callback"
DESCRIPTION = "Ask for access to company apps in a direct message."
BACKGROUND_COLOR = "#4f46e5"


def oauth_redirect_url() -> str | None:
    """Slack sends the browser back here after "Allow". Only an https panel address qualifies."""
    if not settings.public_url.startswith("https://"):
        return None
    return f"{settings.public_url}{CALLBACK_PATH}"


def build_manifest(bot_name: str) -> dict[str, Any]:
    oauth: dict[str, Any] = {"scopes": {"bot": list(BOT_SCOPES)}}
    redirect = oauth_redirect_url()
    if redirect:
        oauth["redirect_urls"] = [redirect]
    return {
        "display_information": {
            "name": bot_name,
            "description": DESCRIPTION,
            "background_color": BACKGROUND_COLOR,
        },
        "features": {
            "app_home": {
                "home_tab_enabled": False,
                "messages_tab_enabled": True,
                "messages_tab_read_only_enabled": False,
            },
            "bot_user": {"display_name": bot_name, "always_online": True},
        },
        "oauth_config": oauth,
        "settings": {
            "event_subscriptions": {"bot_events": list(BOT_EVENTS)},
            "interactivity": {"is_enabled": True},
            "org_deploy_enabled": False,
            "socket_mode_enabled": True,
            "token_rotation_enabled": False,
        },
    }
