"""Development: fictional people and accounts for a fresh database without SEED_GOOGLE_* in `.env`.

A ``fake`` connection is the people source (12 people at example.com, invented names, one
service account) and gives the dashboard accounts, alerts and discovered apps to show. Needs the
fake connector (``OPEN_REVOKE_ENABLE_FAKE_CONNECTOR``, on in compose.dev.yaml); without it, or
with a real Google Workspace seeded, nothing is added.
"""

from decimal import Decimal
from typing import TYPE_CHECKING

from app.connectors.registry import fake_connector_enabled
from app.db.seed_google import configured as google_configured
from app.models.enums import Integration, PricingModel
from app.schemas.apps import AppCreate, PriceIn
from app.schemas.connections import ConnectionUpsert
from app.services.apps import create_app
from app.services.connections import upsert_connection

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

DIRECTORY_NAME = "Example Directory"


def enabled() -> bool:
    return fake_connector_enabled() and not google_configured()


async def seed_demo_directory(session: AsyncSession) -> None:
    if not enabled():
        return
    app = await create_app(
        session,
        AppCreate(
            name=DIRECTORY_NAME,
            integration=Integration.API,
            pricing_model=PricingModel.PER_SEAT,
            price=PriceIn(amount=Decimal(6), currency="USD"),
        ),
    )
    await upsert_connection(
        session,
        app.id,
        ConnectionUpsert(
            connector_key="fake",
            config={"domain": "example.com", "accounts": 12, "mode": "ok", "write_mode": "apply"},
            secrets={"token": "dev-token"},
            is_people_source=True,
        ),
    )
