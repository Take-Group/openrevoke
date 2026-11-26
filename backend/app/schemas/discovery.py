"""App discovery: scans of the identity provider and the third-party apps people sign in to."""

import uuid
from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field

from app.models.enums import (
    ConnectionStatus,
    DirectoryStatus,
    DiscoveredAppStatus,
    PersonStatus,
    ScanRunStatus,
)
from app.schemas.catalog import CatalogMatchOut
from app.schemas.common import ApiModel


class GrantRisk(StrEnum):
    """Why a sign-in needs attention. Null risk means the person is active everywhere."""

    LEFT = "left"  # the person has status left in Open Revoke
    SUSPENDED = "suspended"  # suspended or archived in the directory
    DELETED = "deleted"  # no longer in the directory


class ScanRunOut(ApiModel):
    id: uuid.UUID
    connection_id: uuid.UUID
    started_at: datetime
    finished_at: datetime | None
    status: ScanRunStatus
    events_from: datetime | None = Field(description="Start of the audit log window that was read")
    events_until: datetime | None
    users_scanned: int
    apps_found: int
    apps_new: int
    grants_found: int
    token_inventory: bool | None = Field(
        description="False when the token inventory scope was not delegated; null while running"
    )
    notes: list[str] | None
    error: str | None


class ScanRunPage(BaseModel):
    items: list[ScanRunOut]
    total: int


class DiscoveryConnector(BaseModel):
    """A connector that can scan, with the scopes the admin delegates for it."""

    key: str
    display_name: str
    required_scopes: list[str]
    optional_scopes: list[str]


class DiscoverySource(BaseModel):
    connection_id: uuid.UUID
    app_id: uuid.UUID
    app_name: str
    connector_key: str
    connection_status: ConnectionStatus
    last_synced_at: datetime | None


class DiscoveryCounts(BaseModel):
    apps: int
    apps_new: int = Field(description="Apps nobody reviewed yet")
    apps_tracked: int
    apps_ignored: int
    people: int = Field(description="Distinct e-mail addresses that signed in to an app that is not ignored")
    grants_at_risk: int = Field(description="Sign-ins of people who left, are suspended or deleted")
    apps_at_risk: int


class DiscoveryOverview(BaseModel):
    source: DiscoverySource | None = Field(description="Null until an identity provider is connected")
    connectors: list[DiscoveryConnector]
    last_scan: ScanRunOut | None
    last_successful_scan: ScanRunOut | None
    scan_running: bool
    counts: DiscoveryCounts
    google_oauth_redirect_uri: str = Field(
        description="Authorized redirect URI to add to the company's Google OAuth client (Connect with Google)"
    )


class DiscoverySourceCreate(BaseModel):
    """Google Workspace for the first scan. The app and its connection are created together."""

    admin_email: str = Field(pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$", max_length=320)
    service_account_json: str = Field(min_length=2, description="JSON key of the service account")
    customer: str = Field(default="my_customer", min_length=1, max_length=100)
    domain: str | None = Field(default=None, max_length=255)


class GoogleOAuthStart(BaseModel):
    """The company's own OAuth client (Google Cloud, type Web application, consent screen Internal)."""

    client_id: str = Field(
        min_length=20, max_length=300, pattern=r"^\S+\.apps\.googleusercontent\.com$", description="OAuth client ID"
    )
    client_secret: str = Field(min_length=1, max_length=300)
    customer: str = Field(default="my_customer", min_length=1, max_length=100)
    domain: str | None = Field(default=None, max_length=255)


class GoogleOAuthStartOut(BaseModel):
    authorization_url: str = Field(description="Google's consent screen; the panel opens it in the same tab")


class LinkedApp(BaseModel):
    id: uuid.UUID
    name: str


class DiscoveredAppOut(BaseModel):
    id: uuid.UUID
    name: str = Field(description="Name from the app's Google consent screen")
    catalog: CatalogMatchOut | None = Field(description="Full name, website and logo from the app catalog")
    status: DiscoveredAppStatus
    app: LinkedApp | None = Field(description="The app in Open Revoke this one is tracked as")
    client_ids: list[str]
    scopes: list[str]
    first_seen_at: datetime | None
    last_seen_at: datetime | None = Field(description="Last sign-in seen in the audit log")
    users: int = Field(description="People who signed in")
    users_at_risk: int = Field(description="Of them: left, suspended or deleted")
    active_tokens: int | None = Field(description="People who hold a token now; null without the token inventory")


class DiscoveredAppPage(BaseModel):
    items: list[DiscoveredAppOut]
    total: int


class GrantPerson(BaseModel):
    id: uuid.UUID
    name: str
    status: PersonStatus


class DiscoveredGrantOut(BaseModel):
    id: uuid.UUID
    email: str
    person: GrantPerson | None = Field(description="Matched by primary e-mail or alias when read")
    directory_status: DirectoryStatus
    deleted_at: datetime | None
    first_seen_at: datetime | None
    last_seen_at: datetime | None
    token_active: bool | None = Field(description="Holds a token now; null without the token inventory")
    scopes: list[str]
    risk: GrantRisk | None


class DiscoveredAppDetail(DiscoveredAppOut):
    grants: list[DiscoveredGrantOut] = Field(description="At-risk people first, then by last sign-in")
    accounts_created: int | None = Field(
        default=None, description="Only in the answer to track with create_accounts: accounts it added"
    )


class DiscoveredAppUpdate(BaseModel):
    """``status`` new or ignored. ``app_id`` links to an app (status tracked); null unlinks (status new)."""

    status: DiscoveredAppStatus | None = None
    app_id: uuid.UUID | None = None


class DiscoveredAppTrack(BaseModel):
    """Creates a manual app in Open Revoke (or links one with the same name) and tracks this one as it."""

    name: str | None = Field(default=None, min_length=1, max_length=200, description="Defaults to the found name")
    create_accounts: bool = Field(
        default=False,
        description="Also add an active account for every person who signed in and is active in the directory. "
        "Only for apps without a connector. Off by default: a Google sign-in does not prove a paid seat",
    )


class PersonDiscoveredApp(BaseModel):
    """An app a person signed in to with their work account."""

    discovered_app_id: uuid.UUID
    name: str
    catalog: CatalogMatchOut | None
    status: DiscoveredAppStatus
    app: LinkedApp | None
    email: str
    directory_status: DirectoryStatus
    first_seen_at: datetime | None
    last_seen_at: datetime | None
    token_active: bool | None
    has_account: bool = Field(description="The person has a not-removed account in the linked app")


class PersonDiscoveredAppPage(BaseModel):
    items: list[PersonDiscoveredApp]
    total: int
