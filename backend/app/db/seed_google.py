"""Development: the Google Workspace connection from `.env` (SEED_GOOGLE_*), recreated by every reset.

Same app and connection as Connect with Google makes (people source, OAuth credentials), without
calling Google: `db reset` starts a sync and a scan afterwards (``start_seed_syncs``).
"""

from typing import TYPE_CHECKING

from sqlalchemy import select

from app.config import settings
from app.connectors.registry import get_connector
from app.models import Connection
from app.models.enums import Integration
from app.schemas.apps import AppCreate
from app.schemas.connections import ConnectionUpsert
from app.services.apps import create_app
from app.services.connections import upsert_connection
from app.services.discovery_setup import GOOGLE_APP_NAME, GOOGLE_KEY

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


def configured() -> bool:
    return bool(
        settings.seed_google_admin_email
        and settings.seed_google_oauth_client_id
        and settings.seed_google_oauth_client_secret
        and settings.seed_google_oauth_refresh_token
    )


async def seed_google_workspace(session: AsyncSession) -> None:
    if not configured():
        return
    assert settings.seed_google_oauth_client_secret and settings.seed_google_oauth_refresh_token  # noqa: S101
    connector = get_connector(GOOGLE_KEY)
    app = await create_app(
        session, AppCreate(name=GOOGLE_APP_NAME, integration=Integration.API, admin_url=connector.admin_url)
    )
    config = {
        "admin_email": settings.seed_google_admin_email,
        "customer": "my_customer",
        "domain": None,
        "oauth_client_id": settings.seed_google_oauth_client_id,
    }
    secrets = {
        "oauth_client_secret": settings.seed_google_oauth_client_secret.get_secret_value(),
        "oauth_refresh_token": settings.seed_google_oauth_refresh_token.get_secret_value(),
    }
    await upsert_connection(
        session,
        app.id,
        ConnectionUpsert(connector_key=GOOGLE_KEY, config=config, secrets=secrets, is_people_source=True),
    )


async def start_seed_syncs() -> None:
    """First sync and scan of the seeded people source (Google Workspace from `.env` or the fake
    directory), so people, accounts and apps are in the panel within a minute."""
    from app.database import async_session
    from app.services.scan_requests import request_scan
    from app.services.sync_requests import request_sync
    from app.temporal.dispatcher import get_sync_dispatcher
    from app.temporal.scan_dispatcher import get_scan_dispatcher

    async with async_session() as session:
        connection = await session.scalar(select(Connection).where(Connection.is_people_source.is_(True)))
        if connection is None:
            return
        await request_sync(session, connection.app_id, get_sync_dispatcher())
        await request_scan(session, get_scan_dispatcher(), connection.id)
