"""The app catalog: full name, website and logo of known SaaS apps, for apps found by a scan.

Google tells a scan only the name from the app's OAuth consent screen and its OAuth client id.
Both are the same in every Google Workspace, because the app's vendor sets them, so one list in
the repo (``apps.json``) names the app for every company. The client id identifies the app; the
name is a weaker hint, because any OAuth app can call itself "Slack". Read
``skills/backend/app-catalog.md`` before changing the matching.
"""

import json
import re
from dataclasses import dataclass
from enum import StrEnum
from functools import cache
from pathlib import Path
from urllib.parse import urlparse

CATALOG_DIR = Path(__file__).resolve().parent
LOGO_DIR = CATALOG_DIR / "logos"
LOGO_URL = "/api/catalog/logos/{slug}.png"
_SLUG = re.compile(r"^[a-z0-9][a-z0-9-]*$")

# Catalog apps a connector can read: picking one in "Add app" suggests that connector.
CONNECTOR_BY_SLUG = {
    "slack": "slack",
    "github": "github",
    "google-workspace": "google_workspace",
    "claude": "claude",
    "chatgpt": "chatgpt",
}

# Shown first in "Add several apps" before the admin searches: tools most companies of 20-250 people pay for.
POPULAR = (
    "google-workspace",
    "slack",
    "notion",
    "github",
    "figma",
    "zoom",
    "jira",
    "confluence",
    "chatgpt",
    "claude",
    "miro",
    "canva",
    "hubspot",
    "asana",
    "trello",
    "dropbox",
    "1password",
    "linear",
    "loom",
    "calendly",
    "docusign",
    "salesforce",
    "zendesk",
    "monday",
    "clickup",
    "airtable",
    "intercom",
    "adobe-creative-cloud",
    "cursor",
    "grammarly",
)


class MatchedBy(StrEnum):
    CLIENT_ID = "client_id"  # the OAuth client id is on the list: this is the app
    NAME = "name"  # only the name matches: probably the app, not proven


@dataclass(frozen=True)
class CatalogApp:
    slug: str
    name: str
    website: str
    logo_slug: str | None  # file in ``logos/``; another app's slug when it shares the logo
    keys: tuple[str, ...]  # normalized names this app is found by
    client_ids: tuple[str, ...]

    @property
    def logo_url(self) -> str | None:
        return LOGO_URL.format(slug=self.logo_slug) if self.logo_slug else None

    @property
    def connector_key(self) -> str | None:
        return CONNECTOR_BY_SLUG.get(self.slug)


@dataclass(frozen=True)
class CatalogMatch:
    app: CatalogApp
    matched_by: MatchedBy


def normalize(name: str) -> str:
    """Lowercase letters and digits only: "Fireflies.ai", "fireflies ai" and "FirefliesAI" are one key."""
    return re.sub(r"[^a-z0-9]", "", name.lower())


def _host(website: str) -> str:
    host = urlparse(website).hostname or ""
    return host.removeprefix("www.")


class AppCatalog:
    def __init__(self, apps: list[CatalogApp]) -> None:
        self.apps = apps
        self._by_slug = {app.slug: app for app in apps}
        self._by_client = {client_id: app for app in apps for client_id in app.client_ids}
        self._by_key: dict[str, CatalogApp] = {}
        for app in apps:
            for key in app.keys:
                self._by_key.setdefault(key, app)

    def get(self, slug: str) -> CatalogApp | None:
        return self._by_slug.get(slug)

    def by_name(self, name: str) -> CatalogApp | None:
        return self._by_key.get(normalize(name)) if name else None

    def match(self, name: str, client_ids: list[str]) -> CatalogMatch | None:
        """By OAuth client id first; when two listed apps share the ids, the one with this name wins."""
        by_client = [self._by_client[client_id] for client_id in client_ids if client_id in self._by_client]
        if by_client:
            named = self.by_name(name)
            return CatalogMatch(named if named in by_client else by_client[0], MatchedBy.CLIENT_ID)
        named = self.by_name(name)
        return CatalogMatch(named, MatchedBy.NAME) if named else None

    def resolve(self, value: str) -> CatalogApp | None:
        """A slug, else a name or alias: what an admin types in a CSV ``app`` column."""
        return self.get(value.strip().lower()) or self.by_name(value)

    def search(self, query: str, limit: int) -> list[CatalogApp]:
        """Apps whose name, alias or website host contains the query; whole and prefix matches first."""
        key = normalize(query)
        if not key:
            return []
        scored: list[tuple[int, str, CatalogApp]] = []
        for app in self.apps:
            name = normalize(app.name)
            if key in (name, app.slug):
                rank = 0
            elif name.startswith(key):
                rank = 1
            elif any(item.startswith(key) for item in app.keys):
                rank = 2
            elif any(key in item for item in app.keys) or key in name:
                rank = 3
            else:
                continue
            scored.append((rank, app.name.lower(), app))
        scored.sort(key=lambda item: item[:2])
        return [app for _, _, app in scored[:limit]]

    def popular(self) -> list[CatalogApp]:
        return [app for app in (self.get(slug) for slug in POPULAR) if app is not None]

    def logo_path(self, slug: str) -> Path | None:
        """The logo file of a slug. Looked up among the files in the folder, so a request never
        builds a path itself."""
        return _logo_files().get(slug)


def _parse(entry: dict) -> CatalogApp:
    slug = entry["slug"]
    names = list(entry.get("aliases", []))
    if entry.get("match_name", True):
        names.append(entry["name"])
    keys = {normalize(name) for name in names} | {normalize(_host(entry["website"]))}
    logo_slug = entry.get("logo") or slug
    return CatalogApp(
        slug=slug,
        name=entry["name"],
        website=entry["website"],
        logo_slug=logo_slug if (LOGO_DIR / f"{logo_slug}.png").is_file() else None,
        keys=tuple(sorted(key for key in keys if key)),
        client_ids=tuple(entry.get("google_client_ids", [])),
    )


@cache
def _logo_files() -> dict[str, Path]:
    return {path.stem: path for path in LOGO_DIR.glob("*.png") if _SLUG.match(path.stem)}


@cache
def app_catalog() -> AppCatalog:
    """Loaded once per process; a change to ``apps.json`` needs an API restart (uvicorn --reload does it)."""
    data = json.loads((CATALOG_DIR / "apps.json").read_text(encoding="utf-8"))
    return AppCatalog([_parse(entry) for entry in data["apps"]])
