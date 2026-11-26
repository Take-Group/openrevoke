"""The app catalog and its logos. Public: the data is in the repo, and the panel's sign-in pages show logos too."""

from typing import Annotated

from fastapi import APIRouter, Query
from fastapi.responses import FileResponse

from app.api.deps import SessionDep
from app.api.params import SearchQuery
from app.catalog.lookup import app_catalog
from app.schemas.catalog import CatalogAppList, CatalogAppOut, CatalogSearchList
from app.services import catalog_search
from app.services.errors import NotFoundError

public_router = APIRouter(prefix="/api/catalog", tags=["catalog"])
# Admins only (domain_router): says which apps this instance has, so it is not public.
router = APIRouter(prefix="/catalog")


@router.get("/search", response_model=CatalogSearchList)
async def search_catalog(
    session: SessionDep, q: SearchQuery = None, limit: Annotated[int, Query(ge=1, le=100)] = 20
) -> CatalogSearchList:
    """Catalog apps for "Add app": by name, alias or website, with the connector that reads them and
    the app already added. Without ``q``: apps discovery found and nobody tracks yet, then popular ones."""
    return CatalogSearchList(items=await catalog_search.search(session, q, limit))


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
