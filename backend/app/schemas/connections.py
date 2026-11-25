import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.models.enums import ConnectionStatus, Integration, SyncRunStatus
from app.schemas.common import ApiModel


class ConnectionOut(ApiModel):
    id: uuid.UUID
    connector_key: str
    config: dict[str, Any] = Field(description="Connector settings without secrets")
    secrets_set: bool = Field(description="True when secrets are stored. Secret values are never returned")
    secret_fields_set: list[str] = Field(
        description="Names of the secret fields that are stored. Values are never returned"
    )
    is_people_source: bool
    writes_enabled: bool
    status: ConnectionStatus
    last_synced_at: datetime | None
    last_error: str | None
    created_at: datetime


class ConnectionUpsert(BaseModel):
    """Saves the connection. Secret fields (``secret: true`` in the connector's ``config_schema``) may come
    in ``config`` or in ``secrets``; they are split out, encrypted and never returned. An empty or missing
    secret keeps the stored value. Changing ``connector_key`` drops the stored secrets."""

    connector_key: str = Field(min_length=1, max_length=100)
    config: dict[str, Any] = Field(default_factory=dict, description="Form values; secret fields allowed")
    secrets: dict[str, str] | None = Field(
        default=None,
        description=(
            "Secret values. Null keeps the stored ones, {} removes all of them; in a non-empty dict a value "
            "replaces the stored one and an empty string keeps it"
        ),
    )
    is_people_source: bool = Field(default=False, description="Needs a connector with list_people")
    writes_enabled: bool = Field(default=False, description="Can be turned on only after a successful sync")


class ConnectionCheckResult(BaseModel):
    ok: bool
    status: ConnectionStatus
    message: str | None


class SyncRunOut(ApiModel):
    id: uuid.UUID
    connection_id: uuid.UUID
    started_at: datetime
    finished_at: datetime | None
    status: SyncRunStatus
    accounts_seen: int
    accounts_added: int
    accounts_removed: int
    error: str | None


class SyncRunPage(BaseModel):
    items: list[SyncRunOut]
    total: int


class ConnectorOut(BaseModel):
    key: str = Field(examples=["slack"])
    display_name: str = Field(examples=["Slack"])
    integration: Integration = Field(description="How the connector reaches the app: api, scim or browser")
    auth_kind: str = Field(description="api_token, google_service_account, scim_token or browser_session")
    capabilities: list[str] = Field(description="list_accounts, create_account, delete_account, list_people")
    config_schema: dict[str, Any] = Field(
        description=(
            "JSON Schema of the connection form: config and secret fields. Secret fields have "
            '"secret": true, "format": "password" and "writeOnly": true; "x-multiline": true asks for a text area'
        )
    )
    secret_fields: list[str] = Field(description="Names of secret fields the form asks for")
    login_url: str | None
    admin_url: str | None
    delete_suspends: bool = Field(
        default=False, description='delete_account suspends the account instead (Google Workspace); UI label "Suspend"'
    )


class ConnectorPage(BaseModel):
    items: list[ConnectorOut]
    total: int
