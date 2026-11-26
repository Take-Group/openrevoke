"""Several apps at once ("Add several apps"): from the catalog or by name, manual and free."""

from typing import TYPE_CHECKING

from sqlalchemy import func, select

from app.catalog.lookup import app_catalog
from app.models import App
from app.schemas.apps import AppBulkCreate, AppBulkResult, AppBulkSkipped, AppCreate
from app.services import audit
from app.services.apps import add_app
from app.services.presenters import app_ref

if TYPE_CHECKING:
    import uuid

    from sqlalchemy.ext.asyncio import AsyncSession


async def existing_apps(session: AsyncSession) -> tuple[dict[str, uuid.UUID], dict[str, uuid.UUID]]:
    """Apps already in Open Revoke, by catalog key and by lowercased name."""
    rows = list(await session.execute(select(App.id, App.catalog_key, func.lower(App.name))))
    by_key = {key: app_id for app_id, key, _ in rows if key}
    by_name = {name: app_id for app_id, _, name in rows}
    return by_key, by_name


async def create_apps(session: AsyncSession, data: AppBulkCreate) -> AppBulkResult:
    """Skips apps that exist (same catalog key or name) or repeat in the request; one audit event."""
    catalog = app_catalog()
    by_key, by_name = await existing_apps(session)
    created: list[App] = []
    skipped: list[AppBulkSkipped] = []
    for item in data.apps:
        entry = catalog.get(item.catalog_key) if item.catalog_key else None
        name = (item.name or (entry.name if entry else "")).strip()
        if item.catalog_key and entry is None:
            skipped.append(_skip(name or item.catalog_key, item.catalog_key, "Not in the catalog"))
            continue
        if not name:
            skipped.append(_skip("", None, "Give a name or a catalog_key"))
            continue
        existing = (by_key.get(entry.slug) if entry else None) or by_name.get(name.lower())
        if existing is not None:
            skipped.append(_skip(name, item.catalog_key, "Already added", existing))
            continue
        app = await add_app(session, AppCreate(name=name, catalog_key=entry.slug if entry else None))
        created.append(app)
        by_name[name.lower()] = app.id
        if entry:
            by_key[entry.slug] = app.id
    if created:
        await audit.record(
            session,
            "app.bulk_created",
            "app",
            None,
            {
                "apps": [{"id": str(app.id), "name": app.name, "catalog_key": app.catalog_key} for app in created],
                "skipped": len(skipped),
            },
        )
    return AppBulkResult(created=[app_ref(app) for app in created], skipped=skipped)


def _skip(name: str, catalog_key: str | None, reason: str, app_id: uuid.UUID | None = None) -> AppBulkSkipped:
    return AppBulkSkipped(name=name, catalog_key=catalog_key, reason=reason, app_id=app_id)
