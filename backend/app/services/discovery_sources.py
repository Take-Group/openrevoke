"""Which connections can scan for apps: connectors with ``Capability.DISCOVER_APPS``."""

from typing import TYPE_CHECKING

from sqlalchemy import select

from app.connectors.base import Capability, Connector
from app.connectors.discovery import AppDiscovery
from app.connectors.registry import all_connectors
from app.models import Connection

if TYPE_CHECKING:
    import uuid

    from sqlalchemy.ext.asyncio import AsyncSession


def discovery_connectors() -> list[Connector]:
    return [
        connector
        for connector in all_connectors()
        if connector.supports(Capability.DISCOVER_APPS) and isinstance(connector, AppDiscovery)
    ]


def discovery_keys() -> list[str]:
    return [connector.key for connector in discovery_connectors()]


async def discovery_connections(session: AsyncSession) -> list[Connection]:
    """Discovery connections, oldest first. The first one is the panel's default source."""
    return list(
        await session.scalars(
            select(Connection)
            .where(Connection.connector_key.in_(discovery_keys()))
            .order_by(Connection.created_at, Connection.id)
        )
    )


async def discovery_connection_ids(session: AsyncSession) -> list[uuid.UUID]:
    return [connection.id for connection in await discovery_connections(session)]
