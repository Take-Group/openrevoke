"""Catalog search for "Add app" and "Add several apps": what is added already, what discovery found."""

from typing import TYPE_CHECKING

from sqlalchemy import func, select

from app.catalog.lookup import CatalogApp, app_catalog
from app.models import DiscoveredApp, DiscoveredGrant
from app.models.enums import DiscoveredAppStatus
from app.schemas.catalog import CatalogSearchItem
from app.services.apps_bulk import existing_apps

if TYPE_CHECKING:
    import uuid

    from sqlalchemy.ext.asyncio import AsyncSession


async def search(session: AsyncSession, q: str | None, limit: int) -> list[CatalogSearchItem]:
    """With ``q``: name, alias and website matches. Without: apps discovery found and nobody tracks yet
    (most people first), then the popular ones, then the rest A to Z."""
    catalog = app_catalog()
    found = await discovered_untracked(session)
    if q and q.strip():
        apps = catalog.search(q, limit)
    else:
        ranked = sorted(found, key=lambda slug: -found[slug])
        apps = [entry for entry in (catalog.get(slug) for slug in ranked) if entry is not None]
        seen = {entry.slug for entry in apps}
        apps += [entry for entry in catalog.popular() if entry.slug not in seen]
        if len(apps) < limit:  # fill the grid with the rest, A to Z
            seen = {entry.slug for entry in apps}
            apps += sorted((entry for entry in catalog.apps if entry.slug not in seen), key=lambda e: e.name.lower())
        apps = apps[:limit]
    by_key, by_name = await existing_apps(session)
    return [_item(entry, by_key, by_name, found) for entry in apps]


async def discovered_untracked(session: AsyncSession) -> dict[str, int]:
    """Catalog slug to people who signed in, for discovered apps that are new (not tracked, not ignored)."""
    rows = await session.execute(
        select(DiscoveredApp.name, DiscoveredApp.client_ids, func.count(DiscoveredGrant.id))
        .outerjoin(DiscoveredGrant, DiscoveredGrant.discovered_app_id == DiscoveredApp.id)
        .where(DiscoveredApp.status == DiscoveredAppStatus.NEW)
        .group_by(DiscoveredApp.id)
    )
    catalog = app_catalog()
    users: dict[str, int] = {}
    for name, client_ids, count in rows:
        match = catalog.match(name, list(client_ids or []))
        if match is not None:
            users[match.app.slug] = users.get(match.app.slug, 0) + count
    return users


def _item(
    entry: CatalogApp, by_key: dict[str, uuid.UUID], by_name: dict[str, uuid.UUID], found: dict[str, int]
) -> CatalogSearchItem:
    return CatalogSearchItem(
        slug=entry.slug,
        name=entry.name,
        website=entry.website,
        logo_url=entry.logo_url,
        connector_key=entry.connector_key,
        already_added=by_key.get(entry.slug) or by_name.get(entry.name.lower()),
        discovered_users=found.get(entry.slug),
    )
