"""First run: connect Google Workspace in one step and start the first sync and scan.

The panel's onboarding calls this with a service account key (``service_account_form``) or, after
"Connect with Google", with the OAuth credentials (``google_oauth.py``). It checks the directory and
the audit log scope before saving anything, so a wrong key or a missing scope leaves no half-made app.
"""

import asyncio
from typing import TYPE_CHECKING

import httpx

from app.connectors.base import ConnectorContext
from app.connectors.errors import ConnectorError
from app.connectors.google_workspace import discovery as google_discovery
from app.connectors.http import build_http_client
from app.models.enums import Integration
from app.schemas.apps import AppCreate
from app.schemas.connections import ConnectionUpsert
from app.services.apps import create_app
from app.services.connections import upsert_connection
from app.services.connector_runtime import HttpFactory, parse_config, resolve_connector
from app.services.discovery_sources import discovery_connections
from app.services.errors import ConflictError, InvalidInputError
from app.services.scan_requests import request_scan
from app.services.sync_dispatch import upsert_schedule_quietly
from app.services.sync_requests import request_sync

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from app.schemas.discovery import DiscoverySourceCreate
    from app.services.scan_dispatch import ScanDispatcher
    from app.services.sync_dispatch import SyncDispatcher

GOOGLE_KEY = "google_workspace"
GOOGLE_APP_NAME = "Google Workspace"
VERIFY_TIMEOUT_SECONDS = 60


type Config = dict[str, str | None]


def service_account_form(data: DiscoverySourceCreate) -> tuple[Config, dict[str, str]]:
    config = {"admin_email": data.admin_email.strip(), "customer": data.customer.strip(), "domain": data.domain}
    return config, {"service_account_json": data.service_account_json.strip()}


async def ensure_no_source(session: AsyncSession) -> None:
    if await discovery_connections(session):
        raise ConflictError("Google Workspace is already connected. Run a scan, or edit the connection in Apps")


async def verify_google(config: Config, secrets: dict[str, str], http_factory: HttpFactory = build_http_client) -> None:
    """Read the directory once and get an audit log token. ``InvalidInputError`` says what is wrong."""
    connector = resolve_connector(GOOGLE_KEY)
    try:
        parsed = parse_config(connector, config, secrets)
        async with asyncio.timeout(VERIFY_TIMEOUT_SECONDS), http_factory() as http:
            ctx = ConnectorContext(config=parsed, secrets=secrets, http=http)
            await connector.check(ctx)
            await google_discovery.audit_token(ctx)
    except ConnectorError as exc:
        raise InvalidInputError(str(exc)) from exc
    except TimeoutError as exc:
        raise InvalidInputError(f"Google did not answer within {VERIFY_TIMEOUT_SECONDS} seconds") from exc
    except httpx.HTTPError as exc:
        raise InvalidInputError(f"Network error while reaching Google: {exc}") from exc


async def setup_google_source(
    session: AsyncSession,
    config: Config,
    secrets: dict[str, str],
    sync_dispatcher: SyncDispatcher,
    scan_dispatcher: ScanDispatcher,
    http_factory: HttpFactory = build_http_client,
) -> None:
    """Create the Google Workspace app and connection (people source), then start a sync and a scan."""
    await ensure_no_source(session)
    await verify_google(config, secrets, http_factory)
    connector = resolve_connector(GOOGLE_KEY)
    app = await create_app(
        session, AppCreate(name=GOOGLE_APP_NAME, integration=Integration.API, admin_url=connector.admin_url)
    )
    connection = await upsert_connection(
        session,
        app.id,
        ConnectionUpsert(connector_key=GOOGLE_KEY, config=config, secrets=secrets, is_people_source=True),
    )
    await session.commit()
    await upsert_schedule_quietly(sync_dispatcher, connection.id)
    await request_sync(session, app.id, sync_dispatcher)
    await request_scan(session, scan_dispatcher, connection.id)
