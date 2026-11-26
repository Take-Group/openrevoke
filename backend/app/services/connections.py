"""Connections: connector catalog, saving a connection with its secrets, connection check."""

import asyncio
from typing import TYPE_CHECKING, Any

import httpx
from pydantic import ValidationError
from sqlalchemy import exists, select

from app.connectors.base import Capability, Connector, ConnectorError, NeedsLogin
from app.connectors.http import build_http_client
from app.connectors.registry import UnknownConnectorError, all_connectors, get_connector
from app.models import Action, App, Connection, SyncRun
from app.models.enums import ActionKind, ActionStatus, ConnectionStatus, Integration, SyncRunStatus
from app.schemas.connections import ConnectionCheckResult, ConnectionUpsert, ConnectorOut
from app.services import actions, audit
from app.services.connector_runtime import HttpFactory, format_validation_error, open_context
from app.services.errors import InvalidInputError, NotFoundError
from app.services.secret_box import SecretsUnreadableError, decrypt_secrets, encrypt_secrets

if TYPE_CHECKING:
    import uuid

    from sqlalchemy.ext.asyncio import AsyncSession

CHECK_TIMEOUT_SECONDS = 60


def connector_out(connector: Connector) -> ConnectorOut:
    return ConnectorOut(
        key=connector.key,
        display_name=connector.display_name,
        integration=connector.integration,
        auth_kind=connector.auth_kind,
        capabilities=sorted(connector.capabilities),
        config_schema=connector.form_schema(),
        secret_fields=connector.secret_fields(),
        login_url=connector.login_url,
        admin_url=connector.admin_url,
        delete_suspends=connector.delete_suspends,
    )


def catalog() -> list[ConnectorOut]:
    return [connector_out(connector) for connector in all_connectors()]


async def get_app_connection(session: AsyncSession, app_id: uuid.UUID) -> tuple[App, Connection | None]:
    app = await session.get(App, app_id)
    if app is None:
        raise NotFoundError("App not found")
    connection = await session.scalar(select(Connection).where(Connection.app_id == app_id))
    return app, connection


async def has_successful_sync(session: AsyncSession, connection_id: uuid.UUID) -> bool:
    return bool(
        await session.scalar(
            select(exists().where(SyncRun.connection_id == connection_id, SyncRun.status == SyncRunStatus.OK))
        )
    )


async def upsert_connection(session: AsyncSession, app_id: uuid.UUID, data: ConnectionUpsert) -> Connection:
    app, connection = await get_app_connection(session, app_id)
    if app.integration == Integration.MANUAL:
        raise InvalidInputError("Change the app's integration from 'manual' before connecting it")
    try:
        connector = get_connector(data.connector_key)
    except UnknownConnectorError as exc:
        raise InvalidInputError(str(exc)) from exc
    if data.is_people_source and not connector.supports(Capability.LIST_PEOPLE):
        raise InvalidInputError(f"{connector.display_name} cannot be a people source")

    same_connector = connection is not None and connection.connector_key == connector.key
    stored: dict[str, str] = {}
    if same_connector and connection is not None:
        try:
            stored = decrypt_secrets(connection.secrets_encrypted)
        except SecretsUnreadableError:
            stored = {}  # the form must send them again; validation below says which are missing
    config, secrets = split_form(connector, data, stored)
    if (
        stored
        and connection is not None
        and connector.endpoint_of(connection.config or {}) != connector.endpoint_of(config)
    ):
        # A stored token never follows a changed URL: the form must send the secrets again.
        stored = {}
        config, secrets = split_form(connector, data, stored)

    # A new organisation, domain or workspace is a new target: the old sync says nothing about it.
    same_target = (
        same_connector
        and connection is not None
        and connector.target_of(connection.config or {}) == connector.target_of(config)
    )
    # Writes switch off by themselves when the target changes; the admin enables them after a new sync.
    target_changed = same_connector and not same_target
    writes_enabled = data.writes_enabled and not target_changed
    already_enabled = same_target and connection is not None and connection.writes_enabled
    if (
        writes_enabled
        and not already_enabled
        and (
            not same_target
            or connection is None
            or connection.last_synced_at is None
            or not await has_successful_sync(session, connection.id)
        )
    ):
        raise InvalidInputError("Writes can be enabled only after a successful sync of this connector")

    created = connection is None
    if connection is None:
        connection = Connection(app_id=app.id, status=ConnectionStatus.NEVER_SYNCED)
        session.add(connection)
    elif not same_target:
        connection.status = ConnectionStatus.NEVER_SYNCED
        connection.last_error = None
        connection.last_synced_at = None
        if target_changed:
            await cancel_waiting_writes(session, app.id)
    changed_secrets = sorted(key for key in set(secrets) | set(stored) if secrets.get(key) != stored.get(key))
    connection.connector_key = connector.key
    connection.config = config
    connection.secrets_encrypted = encrypt_secrets(secrets)
    connection.is_people_source = data.is_people_source
    connection.writes_enabled = writes_enabled
    await session.flush()
    await audit.record(
        session,
        "connection.created" if created else "connection.updated",
        "connection",
        connection.id,
        {
            "app_id": str(app.id),
            "connector_key": connector.key,
            "config": config,
            "secrets_changed": changed_secrets,
            "is_people_source": data.is_people_source,
            "writes_enabled": writes_enabled,
            "target_changed": target_changed,
        },
    )
    await session.refresh(connection)  # loads server defaults (created_at) for the response
    return connection


async def cancel_waiting_writes(session: AsyncSession, app_id: uuid.UUID) -> None:
    """Writes approved or waiting for the old target must not run against the new one."""
    waiting = await session.scalars(
        select(Action.id).where(
            Action.app_id == app_id,
            Action.kind != ActionKind.MANUAL_TASK,
            Action.status.in_([ActionStatus.PENDING_APPROVAL, ActionStatus.APPROVED]),
        )
    )
    for action_id in list(waiting):
        await actions.cancel(session, action_id)


def split_form(
    connector: Connector, data: ConnectionUpsert, stored: dict[str, str]
) -> tuple[dict[str, Any], dict[str, str]]:
    """Split the form into plain config and secrets, merge with stored secrets, validate both together."""
    secret_names = set(connector.secret_fields())
    known = set(connector.config_schema.model_fields)
    unknown = sorted((set(data.config) - known) | (set(data.secrets or {}) - secret_names))
    if unknown:
        raise InvalidInputError(f"Unknown fields for {connector.display_name}: {', '.join(unknown)}")

    secrets = dict(stored)
    if data.secrets == {}:
        secrets = {}
    for source in (data.secrets or {}, {key: data.config[key] for key in secret_names if key in data.config}):
        for key, value in source.items():
            if isinstance(value, str) and value.strip():
                secrets[key] = value.strip()
    config_in = {key: value for key, value in data.config.items() if key not in secret_names}
    try:
        parsed = connector.config_schema.model_validate({**config_in, **secrets})
    except ValidationError as exc:
        raise InvalidInputError(f"Invalid connection settings: {format_validation_error(exc)}") from exc
    config = parsed.model_dump(mode="json", exclude=secret_names)
    return config, {key: value for key, value in secrets.items() if key in secret_names}


async def set_status(
    session: AsyncSession, connection: Connection, status: ConnectionStatus, error: str | None = None
) -> None:
    """Change the connection status; a change is written to the audit log."""
    previous = connection.status
    connection.status = status
    connection.last_error = error
    await session.flush()
    if previous != status:
        await audit.record(
            session,
            "connection.status_changed",
            "connection",
            connection.id,
            {"old": str(previous), "new": str(status), "error": error},
        )


async def check_connection(
    session: AsyncSession, app_id: uuid.UUID, http_factory: HttpFactory = build_http_client
) -> ConnectionCheckResult:
    """Call the connector's ``check``. Only a login problem changes the connection status."""
    _, connection = await get_app_connection(session, app_id)
    if connection is None:
        raise NotFoundError("The app has no connection")
    try:
        async with asyncio.timeout(CHECK_TIMEOUT_SECONDS), open_context(connection, http_factory) as (connector, ctx):
            result = await connector.check(ctx)
    except NeedsLogin as exc:
        await set_status(session, connection, ConnectionStatus.NEEDS_LOGIN, str(exc))
        return ConnectionCheckResult(ok=False, status=connection.status, message=str(exc))
    except (ConnectorError, SecretsUnreadableError) as exc:
        return ConnectionCheckResult(ok=False, status=connection.status, message=str(exc))
    except TimeoutError:
        message = f"The app did not answer within {CHECK_TIMEOUT_SECONDS} seconds"
        return ConnectionCheckResult(ok=False, status=connection.status, message=message)
    except httpx.HTTPError as exc:
        return ConnectionCheckResult(ok=False, status=connection.status, message=f"Network error: {exc}")
    if result.ok and connection.status == ConnectionStatus.NEEDS_LOGIN:
        recovered = ConnectionStatus.OK if connection.last_synced_at else ConnectionStatus.NEVER_SYNCED
        await set_status(session, connection, recovered)
    return ConnectionCheckResult(ok=result.ok, status=connection.status, message=result.message)
