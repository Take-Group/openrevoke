from datetime import datetime

from pydantic import BaseModel, Field, SecretStr

from app.models.enums import SlackAgentStatus

BOT_NAME_PATTERN = r"^[A-Za-z0-9][A-Za-z0-9 ._-]*$"


class SlackAgentOut(BaseModel):
    status: SlackAgentStatus
    enabled: bool
    bot_name: str | None
    app_id: str | None
    team_name: str | None
    bot_user_id: str | None
    has_bot_token: bool
    has_app_token: bool
    has_config_token: bool = Field(description="An app configuration token is saved: the icon can be changed")
    avatar_set_at: datetime | None
    avatar_error: str | None
    last_error: str | None
    connected_at: datetime | None
    ai_configured: bool = Field(description="The language model is set up (GET /api/ai-settings)")
    install_url: str | None = Field(description="Where the admin installs the app: OAuth when the panel is https")
    oauth_install: bool = Field(description="install_url comes back to the panel and saves the bot token by itself")
    app_settings_url: str | None
    app_token_url: str | None = Field(description="Basic Information page, section App-Level Tokens")
    manifest_url: str = Field(description="Creates the app from the manifest by hand, without a configuration token")


class SlackAppCreate(BaseModel):
    config_token: SecretStr = Field(min_length=10, max_length=500, description="App configuration token (xoxe.xoxp-…)")
    config_refresh_token: SecretStr | None = Field(
        default=None, max_length=500, description="Its refresh token (xoxe-…)"
    )
    bot_name: str = Field(default="Open Revoke", min_length=1, max_length=35, pattern=BOT_NAME_PATTERN)


class SlackTokensUpdate(BaseModel):
    """Null keeps the saved token."""

    bot_token: SecretStr | None = Field(default=None, max_length=500, description="Bot User OAuth Token (xoxb-…)")
    app_token: SecretStr | None = Field(default=None, max_length=500, description="App-level token (xapp-…)")


class SlackAgentUpdate(BaseModel):
    enabled: bool


class SlackOAuthStart(BaseModel):
    url: str
