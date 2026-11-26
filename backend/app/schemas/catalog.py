"""The app catalog: known SaaS apps with their full name, website and logo (``app/catalog``)."""

import uuid

from pydantic import Field

from app.catalog.lookup import CatalogApp, CatalogMatch, MatchedBy
from app.schemas.common import ApiModel


class CatalogAppOut(ApiModel):
    slug: str
    name: str = Field(description="Full product name")
    website: str
    logo_url: str | None = Field(description="Bundled logo served by the API; null when the app has none")
    keys: list[str] = Field(description="Normalized names (lowercase letters and digits) this app is found by")

    @classmethod
    def of(cls, app: CatalogApp) -> CatalogAppOut:
        return cls(slug=app.slug, name=app.name, website=app.website, logo_url=app.logo_url, keys=list(app.keys))


class CatalogAppList(ApiModel):
    items: list[CatalogAppOut]


class CatalogSearchItem(ApiModel):
    """A catalog app as "Add app" offers it."""

    slug: str
    name: str
    website: str
    logo_url: str | None
    connector_key: str | None = Field(description="Connector that reads this app's accounts, when there is one")
    already_added: uuid.UUID | None = Field(
        description="Id of the app in Open Revoke with this catalog_key or name; null when not added yet"
    )
    discovered_users: int | None = Field(
        description="People who signed in with Google, when discovery found the app and it is not tracked yet"
    )


class CatalogSearchList(ApiModel):
    items: list[CatalogSearchItem]


class CatalogMatchOut(ApiModel):
    """What the catalog knows about a found app."""

    slug: str
    name: str
    website: str
    logo_url: str | None
    matched_by: MatchedBy = Field(
        description="client_id: the app's Google OAuth client is on the list; name: only the name matches"
    )

    @classmethod
    def of(cls, match: CatalogMatch | None) -> CatalogMatchOut | None:
        if match is None:
            return None
        app = match.app
        return cls(
            slug=app.slug, name=app.name, website=app.website, logo_url=app.logo_url, matched_by=match.matched_by
        )
