"""Where the shared browser comes from.

``BrowserProvider`` hides the engine. ``LocalChromiumProvider`` is the
Chromium of the ``browser`` container, reached over CDP with Playwright's
``connect_over_cdp``. A hosted browser engine would be another provider.

Rules of the local provider (skills/backend/browser.md):

- one connection per process, opened lazily under a lock and reopened when
  it drops (Chromium restarted, container restarted),
- connect by IP: Chrome's DevTools HTTP server rejects a ``Host`` header that
  is a name other than ``localhost``, so ``browser`` is resolved first,
- never ``browser.close()``: on a CDP connection it can close the user's
  Chromium. ``disconnect`` stops the Playwright driver, which only drops the
  WebSocket.
"""

import asyncio
import socket
from dataclasses import dataclass
from functools import lru_cache
from typing import TYPE_CHECKING, Protocol

import httpx
import structlog
from playwright.async_api import Error as PlaywrightError
from playwright.async_api import async_playwright

from app.browser.capture import HeaderCapture
from app.config import settings
from app.connectors.browser_api import BrowserUnavailableError

if TYPE_CHECKING:
    from playwright.async_api import Browser, BrowserContext, Playwright

logger = structlog.get_logger()

CONNECT_TIMEOUT_MS = 15_000
HEALTH_TIMEOUT = httpx.Timeout(3.0)


@dataclass
class BrowserHealth:
    up: bool
    version: str | None = None
    error: str | None = None


@dataclass
class TabInfo:
    id: str
    url: str
    title: str | None


class BrowserProvider(Protocol):
    capture: HeaderCapture

    async def connect(self) -> BrowserContext:
        """The browser context with the admin's profile (cookies, local storage)."""
        ...

    def live_view_url(self) -> str | None: ...

    async def health(self) -> BrowserHealth: ...

    async def tabs(self) -> list[TabInfo]: ...

    async def disconnect(self) -> None: ...


class LocalChromiumProvider:
    def __init__(self, host: str, port: int, live_view_url: str | None) -> None:
        self._host = host
        self._port = port
        self._live_view_url = live_view_url
        self._lock = asyncio.Lock()
        self._playwright: Playwright | None = None
        self._browser: Browser | None = None
        self.capture = HeaderCapture()

    def live_view_url(self) -> str | None:
        return self._live_view_url

    async def _base_url(self) -> str:
        try:
            ip = await asyncio.to_thread(socket.gethostbyname, self._host)
        except OSError as exc:
            raise BrowserUnavailableError(
                f"Browser unavailable: cannot resolve {self._host!r}. Is the browser container running?"
            ) from exc
        return f"http://{ip}:{self._port}"

    async def connect(self) -> BrowserContext:
        async with self._lock:
            if self._browser is not None and self._browser.is_connected() and self._browser.contexts:
                return self._browser.contexts[0]
            await self._drop()
            base_url = await self._base_url()
            try:
                self._playwright = await async_playwright().start()
            except Exception as exc:  # noqa: BLE001 - the driver subprocess fails with plain exceptions
                await self._drop()
                raise BrowserUnavailableError(
                    f"Browser unavailable: the Playwright driver did not start ({_first_line(exc)})"
                ) from exc
            try:
                browser = await self._playwright.chromium.connect_over_cdp(base_url, timeout=CONNECT_TIMEOUT_MS)
            except PlaywrightError as exc:
                await self._drop()
                raise BrowserUnavailableError(
                    f"Browser unavailable: no answer from Chromium at {self._host}:{self._port} ({_first_line(exc)})"
                ) from exc
            if not browser.contexts:
                await self._drop()
                raise BrowserUnavailableError("Browser unavailable: Chromium has no default profile context")
            context = browser.contexts[0]
            self.capture.attach(context)
            self._browser = browser
            logger.info("browser_connected", host=self._host, version=browser.version)
            return context

    async def _drop(self) -> None:
        """Forget the connection. Stopping the driver closes the WebSocket, not Chromium."""
        self._browser = None
        self.capture.clear()
        if self._playwright is not None:
            playwright, self._playwright = self._playwright, None
            try:
                await playwright.stop()
            except Exception as exc:  # noqa: BLE001 - the driver may already be gone
                logger.debug("browser_driver_stop_failed", error=str(exc))

    async def disconnect(self) -> None:
        async with self._lock:
            await self._drop()

    async def _get_json(self, path: str) -> object:
        base_url = await self._base_url()
        async with httpx.AsyncClient(timeout=HEALTH_TIMEOUT) as client:
            response = await client.get(base_url + path)
            response.raise_for_status()
            return response.json()

    async def health(self) -> BrowserHealth:
        try:
            body = await self._get_json("/json/version")
        except (BrowserUnavailableError, httpx.HTTPError, ValueError) as exc:
            return BrowserHealth(up=False, error=_first_line(exc) or exc.__class__.__name__)
        version = body.get("Browser") if isinstance(body, dict) else None
        return BrowserHealth(up=True, version=version if isinstance(version, str) else None)

    async def tabs(self) -> list[TabInfo]:
        """Open tabs from CDP's ``/json/list`` (no Playwright connection needed)."""
        try:
            body = await self._get_json("/json/list")
        except (httpx.HTTPError, ValueError) as exc:
            raise BrowserUnavailableError(f"Browser unavailable: {_first_line(exc)}") from exc
        if not isinstance(body, list):
            return []
        return [
            TabInfo(id=str(item.get("id")), url=str(item.get("url") or ""), title=item.get("title") or None)
            for item in body
            if isinstance(item, dict) and item.get("type") == "page"
        ]


def _first_line(exc: BaseException) -> str:
    return str(exc).strip().splitlines()[0] if str(exc).strip() else exc.__class__.__name__


@lru_cache(maxsize=1)
def get_browser_provider() -> BrowserProvider:
    """The provider of this process (one shared CDP connection per API or worker process)."""
    return LocalChromiumProvider(settings.browser_cdp_host, settings.browser_cdp_port, settings.browser_live_view_url)
