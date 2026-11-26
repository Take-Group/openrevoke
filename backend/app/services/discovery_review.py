"""App discovery, write side: the admin ignores a found app or tracks it as an app in Open Revoke."""

from typing import TYPE_CHECKING

from sqlalchemy import func, select

from app.catalog.lookup import app_catalog
from app.models import App, DiscoveredApp, DiscoveredGrant
from app.models.enums import DirectoryStatus, DiscoveredAppStatus, Integration
from app.schemas.apps import AppCreate
from app.services import audit
from app.services.accounts_import import add_people_accounts
from app.services.apps import create_app
from app.services.errors import InvalidInputError, NotFoundError

if TYPE_CHECKING:
    import uuid

    from sqlalchemy.ext.asyncio import AsyncSession

    from app.schemas.discovery import DiscoveredAppTrack, DiscoveredAppUpdate


async def _get(session: AsyncSession, discovered_app_id: uuid.UUID) -> DiscoveredApp:
    app = await session.get(DiscoveredApp, discovered_app_id)
    if app is None:
        raise NotFoundError("Discovered app not found")
    return app


async def update_discovered_app(
    session: AsyncSession, discovered_app_id: uuid.UUID, data: DiscoveredAppUpdate, fields: set[str]
) -> DiscoveredApp:
    found = await _get(session, discovered_app_id)
    before = {"status": str(found.status), "app_id": str(found.app_id) if found.app_id else None}
    if "app_id" in fields:
        if data.app_id is None:
            found.app_id = None
            found.status = DiscoveredAppStatus.NEW
        else:
            if await session.get(App, data.app_id) is None:
                raise NotFoundError("App not found")
            found.app_id = data.app_id
            found.status = DiscoveredAppStatus.TRACKED
    if "status" in fields and data.status is not None:
        if data.status == DiscoveredAppStatus.TRACKED and found.app_id is None:
            raise InvalidInputError("Link an app (app_id) to track a discovered app")
        if data.status != DiscoveredAppStatus.TRACKED and "app_id" not in fields:
            found.app_id = None
        found.status = data.status
    await session.flush()
    await _record(session, found, before)
    return found


async def track_discovered_app(
    session: AsyncSession, discovered_app_id: uuid.UUID, data: DiscoveredAppTrack
) -> tuple[DiscoveredApp, int | None]:
    """Link the app in Open Revoke with the same name (or catalog key), or create a manual one.

    Without a name from the admin the app gets the catalog's full name ("Fathom", not "fathom.video");
    an app already named either way is linked instead. The catalog key goes on the app, so it gets the
    catalog's logo. With ``create_accounts`` it returns how many accounts it added, else None.
    """
    found = await _get(session, discovered_app_id)
    before = {"status": str(found.status), "app_id": str(found.app_id) if found.app_id else None}
    match = app_catalog().match(found.name, list(found.client_ids or []))
    catalog_key = match.app.slug if match else None
    name = (data.name or (match.app.name if match else found.name)).strip()[:200]
    names = {name.lower()} if data.name else {name.lower(), found.name.strip().lower()}
    app = await session.scalar(select(App).where(func.lower(App.name).in_(names)).limit(1))
    if app is None and catalog_key and not data.name:
        app = await session.scalar(select(App).where(App.catalog_key == catalog_key).limit(1))
    if app is None:
        created = await create_app(
            session, AppCreate(name=name, catalog_key=catalog_key, integration=Integration.MANUAL)
        )
        app = await session.get(App, created.id)
        assert app is not None
    elif app.catalog_key is None and catalog_key:
        app.catalog_key = catalog_key
    found.app_id = app.id
    found.status = DiscoveredAppStatus.TRACKED
    await session.flush()
    await _record(session, found, before)
    return found, await _add_accounts(session, found, app) if data.create_accounts else None


async def _add_accounts(session: AsyncSession, found: DiscoveredApp, app: App) -> int:
    """Accounts for people who signed in and are active in the directory; recorded with the count."""
    emails = list(
        await session.scalars(
            select(DiscoveredGrant.email).where(
                DiscoveredGrant.discovered_app_id == found.id,
                DiscoveredGrant.directory_status == DirectoryStatus.ACTIVE,
            )
        )
    )
    created = await add_people_accounts(session, app, emails, via="discovery")
    await audit.record(
        session,
        "discovery.accounts_created",
        "discovered_app",
        found.id,
        {
            "name": found.name,
            "accounts": created,
            "signed_in": len(emails),
            "manual_app": app.integration == Integration.MANUAL,
        },
        app_id=app.id,
    )
    return created


async def _record(session: AsyncSession, found: DiscoveredApp, before: dict[str, str | None]) -> None:
    after = {"status": str(found.status), "app_id": str(found.app_id) if found.app_id else None}
    if after == before:
        return
    await audit.record(
        session,
        "discovery.app_reviewed",
        "discovered_app",
        found.id,
        {"name": found.name, "old": before, "new": after},
        app_id=found.app_id,
    )
