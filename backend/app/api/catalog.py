"""The app catalog and its logos. Public: the data is in the repo, and the panel's sign-in pages show logos too."""

from fastapi import APIRouter
from fastapi.responses import FileResponse

from app.catalog.lookup import app_catalog
from app.schemas.catalog import CatalogAppList, CatalogAppOut
from app.services.errors import NotFoundError

public_router = APIRouter(prefix="/api/catalog", tags=["catalog"])


@public_router.get("/apps", response_model=CatalogAppList)
async def list_catalog_apps() -> CatalogAppList:
    """Every known app; the panel looks up logos of apps by name with ``keys``."""
    return CatalogAppList(items=[CatalogAppOut.of(app) for app in app_catalog().apps])


@public_router.get("/logos/{slug}.png", response_class=FileResponse)
async def catalog_logo(slug: str) -> FileResponse:
    path = app_catalog().logo_path(slug)
    if path is None:
        raise NotFoundError("Logo not found")
    return FileResponse(path, media_type="image/png", headers={"Cache-Control": "public, max-age=86400"})
