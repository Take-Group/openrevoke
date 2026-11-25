import uuid

from pydantic import BaseModel, Field, model_validator

from app.models.enums import ConnectionStatus, PasswordManager


class BrowserTab(BaseModel):
    id: str
    url: str
    title: str | None
    app_id: uuid.UUID | None = Field(description="App whose login or admin URL matches the tab's origin")


class BrowserApp(BaseModel):
    """An app read through the browser: its login page and whether the last sync found a session."""

    app_id: uuid.UUID
    name: str
    connector_key: str | None = Field(description="Browser connector of the app; null when not connected yet")
    login_url: str | None = Field(description="Page that POST /api/browser/open with app_id opens")
    connection_status: ConnectionStatus | None = Field(
        description="needs_login means the admin has to log in again in the browser; null without a connection"
    )
    last_error: str | None


class BrowserState(BaseModel):
    available: bool = Field(description="False when the browser container is not reachable")
    live_view_url: str | None = Field(
        description="Live view page to embed in an iframe, on the panel's origin; null for users who are not admins"
    )
    tabs: list[BrowserTab]
    version: str | None = Field(default=None, description="Chromium version, e.g. Chrome/156.0.8078.79")
    error: str | None = Field(default=None, description="Why the browser is not available")
    apps: list[BrowserApp] = Field(
        default_factory=list, description="Apps with a browser connector (or integration browser)"
    )


class BrowserPolicyOut(BaseModel):
    """Non-sensitive config the ``browser`` container polls to force-install the admin's password manager."""

    manager: PasswordManager | None = Field(description="The org's chosen password manager, null until picked")
    extension_id: str | None = Field(description="Chrome Web Store id to force-install, null for other/none")


class BrowserOpenRequest(BaseModel):
    """Give exactly one: ``url`` or ``app_id`` (opens the app's login page)."""

    url: str | None = Field(default=None, max_length=2000)
    app_id: uuid.UUID | None = None

    @model_validator(mode="after")
    def _one_target(self) -> BrowserOpenRequest:
        if (self.url is None) == (self.app_id is None):
            raise ValueError("Give exactly one of url or app_id")
        return self
