"""The Browser page: state of the shared browser, apps that log in there, opening a login page."""

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any
from urllib.parse import urlsplit

from sqlalchemy import or_, select

from app.browser.session import CdpBrowserSession, origin_of
from app.connectors.base import AuthKind, Connector
from app.connectors.browser_api import BrowserUnavailableError
from app.connectors.registry import UnknownConnectorError, all_connectors, get_connector
from app.models import App, Connection, Organization
from app.models.enums import Integration, PasswordManager
from app.schemas.browser import BrowserApp, BrowserOpenRequest, BrowserPolicyOut, BrowserState, BrowserTab
from app.services.errors import InvalidInputError, NotFoundError, UnavailableError

# Chrome Web Store ids of the password managers the shared browser can force-install.
# Verified 25.11.2026; 1Password's deploy docs name this id. Others (other/none) install nothing.
PASSWORD_MANAGER_EXTENSIONS: dict[PasswordManager, str] = {
    PasswordManager.ONE_PASSWORD: "aeblfdkhhhdcdjpifhhbdiojplfjncoa",
    PasswordManager.BITWARDEN: "nngceckbapebfimnlniiiahkandclblb",
}


async def password_manager_policy(session: AsyncSession) -> BrowserPolicyOut:
    """What the browser container installs: the org's manager and its extension id (null when none).

    Non-sensitive config the ``browser`` container polls to force-install the right extension.
    """
    organization = await session.get(Organization, 1)
    manager = organization.password_manager if organization else None
    return BrowserPolicyOut(manager=manager, extension_id=PASSWORD_MANAGER_EXTENSIONS.get(manager) if manager else None)


if TYPE_CHECKING:
    import uuid

    from sqlalchemy.ext.asyncio import AsyncSession

    from app.browser.provider import BrowserProvider


@dataclass
class _AppEntry:
    out: BrowserApp
    origins: set[str]


def _browser_connector(key: str | None) -> Connector | None:
    if not key:
        return None
    try:
        connector = get_connector(key)
    except UnknownConnectorError:
        return None
    return connector if connector.auth_kind == AuthKind.BROWSER_SESSION else None


def _app_origins(app: App, connector: Connector | None, config: dict[str, Any]) -> set[str]:
    origins = connector.browser_origins(config) if connector else set()
    if app.admin_url and (origin := origin_of(app.admin_url)):
        origins.add(origin)
    return origins


async def _browser_apps(session: AsyncSession) -> list[_AppEntry]:
    browser_keys = [c.key for c in all_connectors() if c.auth_kind == AuthKind.BROWSER_SESSION]
    rows = await session.execute(
        select(App, Connection)
        .outerjoin(Connection, Connection.app_id == App.id)
        .where(or_(App.integration == Integration.BROWSER, Connection.connector_key.in_(browser_keys)))
        .order_by(App.name)
    )
    entries = []
    for app, connection in rows:
        connector = _browser_connector(connection.connector_key if connection else None)
        config = (connection.config or {}) if connection else {}
        entries.append(
            _AppEntry(
                out=BrowserApp(
                    app_id=app.id,
                    name=app.name,
                    connector_key=connector.key if connector else None,
                    login_url=_login_url(app, connector, config),
                    connection_status=connection.status if connection else None,
                    last_error=connection.last_error if connection else None,
                ),
                origins=_app_origins(app, connector, config),
            )
        )
    return entries


def _login_url(app: App, connector: Connector | None, config: dict[str, Any]) -> str | None:
    return (connector.login_page(config) if connector else None) or app.admin_url


def _tab_app(url: str, entries: list[_AppEntry]) -> uuid.UUID | None:
    origin = origin_of(url)
    if not origin:
        return None
    return next((entry.out.app_id for entry in entries if origin in entry.origins), None)


async def browser_state(session: AsyncSession, provider: BrowserProvider) -> BrowserState:
    entries = await _browser_apps(session)
    health = await provider.health()
    tabs: list[BrowserTab] = []
    error = health.error
    if health.up:
        try:
            tabs = [
                BrowserTab(id=tab.id, url=tab.url, title=tab.title, app_id=_tab_app(tab.url, entries))
                for tab in await provider.tabs()
            ]
        except BrowserUnavailableError as exc:
            error = str(exc)
    return BrowserState(
        available=health.up and error is None,
        live_view_url=provider.live_view_url(),
        tabs=tabs,
        version=health.version,
        error=error,
        apps=[entry.out for entry in entries],
    )


async def _target_url(session: AsyncSession, data: BrowserOpenRequest) -> tuple[str, uuid.UUID | None]:
    if data.url is not None:
        parts = urlsplit(data.url.strip())
        if parts.scheme not in ("http", "https") or not parts.netloc:
            raise InvalidInputError("Give an http:// or https:// URL")
        return data.url.strip(), None
    assert data.app_id is not None
    app = await session.get(App, data.app_id)
    if app is None:
        raise NotFoundError("App not found")
    connection = await session.scalar(select(Connection).where(Connection.app_id == app.id))
    connector = _browser_connector(connection.connector_key if connection else None)
    url = _login_url(app, connector, (connection.config or {}) if connection else {})
    if not url:
        raise InvalidInputError("The app has no browser connector and no admin URL to open")
    return url, app.id


async def open_page(session: AsyncSession, provider: BrowserProvider, data: BrowserOpenRequest) -> BrowserTab:
    """Shows the page in the tab already on its origin, or in a new tab."""
    url, app_id = await _target_url(session, data)
    try:
        await provider.connect()
        tab = await CdpBrowserSession(provider).open_tab(url)
    except BrowserUnavailableError as exc:
        raise UnavailableError(str(exc)) from exc
    except Exception as exc:  # noqa: BLE001 - Playwright and connector errors end as one readable message
        raise InvalidInputError(f"The browser could not open {url}: {exc}") from exc
    if app_id is None:
        app_id = _tab_app(tab.url, await _browser_apps(session))
    return BrowserTab(id=tab.id, url=tab.url, title=tab.title, app_id=app_id)
