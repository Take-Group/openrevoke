"""Turn a stored connection into a connector call: decrypt secrets, parse config, open HTTP."""

from collections.abc import Awaitable, Callable
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING, Any

import httpx
from pydantic import BaseModel, ValidationError

from app.browser.session import open_browser_session
from app.connectors.base import AuthKind, Connector, ConnectorContext
from app.connectors.errors import ConnectorError
from app.connectors.http import build_http_client
from app.connectors.registry import UnknownConnectorError, get_connector
from app.services.secret_box import decrypt_secrets

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from app.connectors.browser_api import BrowserSession
    from app.models import Connection

type HttpFactory = Callable[[], httpx.AsyncClient]
# Returns the shared browser session; raises BrowserUnavailableError (a ConnectorError) when it is down.
type BrowserFactory = Callable[[], Awaitable[BrowserSession]]


def format_validation_error(exc: ValidationError) -> str:
    parts = []
    for error in exc.errors():
        field = ".".join(str(part) for part in error["loc"]) or "config"
        parts.append(f"{field}: {error['msg']}")
    return "; ".join(parts)


def parse_config(connector: Connector, config: dict[str, Any], secrets: dict[str, str]) -> BaseModel:
    """Validate config and secrets together against the connector's form. Raises ``ConnectorError``."""
    try:
        return connector.config_schema.model_validate({**config, **secrets})
    except ValidationError as exc:
        raise ConnectorError(f"Connection settings are incomplete or invalid: {format_validation_error(exc)}") from exc


def resolve_connector(key: str) -> Connector:
    try:
        return get_connector(key)
    except UnknownConnectorError as exc:
        raise ConnectorError(f"Connector {key!r} is not available in this installation") from exc


@asynccontextmanager
async def open_context(
    connection: Connection,
    http_factory: HttpFactory = build_http_client,
    browser_factory: BrowserFactory | None = None,
) -> AsyncIterator[tuple[Connector, ConnectorContext]]:
    """Connector and its context for one connection. Closes the HTTP client afterwards.

    Connectors with ``AuthKind.BROWSER_SESSION`` get ``ctx.browser``. Raises
    ``ConnectorError`` for an unknown connector, invalid settings or a browser
    that is down (``BrowserUnavailableError``: an error, not ``needs_login``),
    and ``SecretsUnreadableError`` when the secrets cannot be decrypted.
    """
    connector = resolve_connector(connection.connector_key)
    secrets = decrypt_secrets(connection.secrets_encrypted)
    config = parse_config(connector, connection.config or {}, secrets)
    browser = None
    if connector.auth_kind == AuthKind.BROWSER_SESSION:
        browser = await (browser_factory or open_browser_session)()
    async with http_factory() as http:
        yield connector, ConnectorContext(config=config, secrets=secrets, http=http, browser=browser)
