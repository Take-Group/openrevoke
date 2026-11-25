"""``BrowserSession`` over CDP: requests run as ``fetch()`` inside the panel's own tab.

The protocol connectors see is ``app.connectors.browser_api.BrowserSession``.
This implementation keeps one tab per origin in the shared browser: it reuses
a tab already on the origin, or opens one (reusing an empty ``about:blank``
tab first). Cookies, origin and anti-CSRF cookies come with the page; auth
headers the panel itself sent are added from ``HeaderCapture``.
"""

import asyncio
import contextlib
import json as jsonlib
from typing import TYPE_CHECKING, Any
from urllib.parse import urlencode, urlsplit

import structlog
from playwright.async_api import Error as PlaywrightError

from app.browser.provider import TabInfo, get_browser_provider
from app.browser.recipe_runner import run_steps
from app.connectors.base import ConnectorError, NeedsLogin
from app.connectors.browser_api import BrowserResponse
from app.recipes.model import render_steps

if TYPE_CHECKING:
    from playwright.async_api import BrowserContext, Page

    from app.browser.provider import BrowserProvider
    from app.recipes.model import Recipe
    from app.recipes.repair import RecipeSupport

logger = structlog.get_logger()

NAVIGATION_TIMEOUT_MS = 45_000
SETTLE_TIMEOUT_MS = 10_000
FETCH_TIMEOUT_SECONDS = 90
BLANK_URLS = frozenset({"about:blank", "chrome://newtab/", "chrome://new-tab-page/"})
# Methods whose request may be sent again when the page navigated while it ran.
SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS"})

FETCH_SCRIPT = """
async ({url, method, headers, body}) => {
  const init = {method, headers, credentials: "include", redirect: "follow"};
  if (body !== null) init.body = body;
  const response = await fetch(url, init);
  const outHeaders = {};
  response.headers.forEach((value, name) => { outHeaders[name] = value; });
  return {status: response.status, url: response.url, headers: outHeaders, text: await response.text()};
}
"""
LOCAL_STORAGE_SCRIPT = "(key) => window.localStorage.getItem(key)"


def origin_of(url: str) -> str:
    """``scheme://host[:port]`` in lower case; empty for ``about:``, ``chrome:`` and other pages."""
    parts = urlsplit(url)
    if parts.scheme not in ("http", "https") or not parts.netloc:
        return ""
    return f"{parts.scheme}://{parts.netloc}".lower()


def _navigation_error(exc: PlaywrightError) -> bool:
    message = str(exc)
    return "Execution context was destroyed" in message or "navigat" in message.lower()


class CdpBrowserSession:
    """One connector call's view of the shared browser. Cheap: the connection lives in the provider."""

    def __init__(self, provider: BrowserProvider, recipe_support: RecipeSupport | None = None) -> None:
        self._provider = provider
        self._recipe_support = recipe_support

    async def _context(self) -> BrowserContext:
        return await self._provider.connect()

    async def _find_page(self, origin: str) -> Page | None:
        context = await self._context()
        for page in context.pages:
            if not page.is_closed() and origin_of(page.url) == origin:
                return page
        return None

    async def _new_page(self, url: str) -> Page:
        context = await self._context()
        blank = next((page for page in context.pages if not page.is_closed() and page.url in BLANK_URLS), None)
        page = blank or await context.new_page()
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=NAVIGATION_TIMEOUT_MS)
        except PlaywrightError as exc:
            if blank is None:
                await page.close()  # no error tabs left behind in the admin's browser
            raise ConnectorError(f"The browser could not open {origin_of(url) or url}: {_short(exc)}") from exc
        return page

    async def _page(self, url: str) -> tuple[Page, bool]:
        """Tab on ``url``'s origin and whether it was opened now."""
        existing = await self._find_page(origin_of(url))
        if existing is not None:
            return existing, False
        return await self._new_page(url), True

    async def _page_on_origin(self, url: str) -> Page | None:
        """Tab that stays on ``url``'s origin. ``None`` when the site redirected the tab away (to a login page)."""
        origin = origin_of(url)
        if not origin:
            raise ConnectorError(f"Not an http(s) URL: {url}")
        page, opened = await self._page(url)
        if opened and origin_of(page.url) == origin:
            # Single-page apps redirect from script after DOMContentLoaded.
            with contextlib.suppress(PlaywrightError):
                await page.wait_for_load_state("load", timeout=SETTLE_TIMEOUT_MS)
        if origin_of(page.url) == origin:
            return page
        if opened:
            landed = origin_of(page.url) or page.url
            logger.info("browser_redirected_away", origin=origin, landed=landed)
            await page.close()  # our own tab; the admin logs in from the Browser page
        return None

    async def _evaluate(self, page: Page, script: str, arg: Any, *, retry: bool = True) -> Any:
        try:
            return await page.evaluate(script, arg)
        except PlaywrightError as exc:
            if not _navigation_error(exc) or not retry:
                raise
        # The page navigated while the script ran: let it settle and try once more.
        with contextlib.suppress(PlaywrightError):
            await page.wait_for_load_state("load", timeout=SETTLE_TIMEOUT_MS)
        return await page.evaluate(script, arg)

    async def open(self, url: str, *, bring_to_front: bool = False) -> str:
        page, _ = await self._page(url)
        if bring_to_front:
            await page.bring_to_front()
        return page.url

    async def open_tab(self, url: str) -> TabInfo:
        """Show ``url`` to the admin: in the tab already on its origin (navigated there) or in a new tab.

        Used by the Browser page ("Log in"). Reusing the tab keeps one tab per app.
        """
        page, opened = await self._page(url)
        if not opened and page.url != url:
            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=NAVIGATION_TIMEOUT_MS)
            except PlaywrightError as exc:
                raise ConnectorError(f"The browser could not open {origin_of(url) or url}: {_short(exc)}") from exc
        await page.bring_to_front()
        cdp = await page.context.new_cdp_session(page)
        try:
            info = await cdp.send("Target.getTargetInfo")
        finally:
            await cdp.detach()
        target = info.get("targetInfo", {})
        return TabInfo(id=str(target.get("targetId", "")), url=page.url, title=await page.title() or None)

    async def fetch(
        self,
        url: str,
        *,
        method: str = "GET",
        json: Any = None,
        form: dict[str, str] | None = None,
        headers: dict[str, str] | None = None,
        auth: bool = True,
        page_url: str | None = None,
        idempotent: bool | None = None,
    ) -> BrowserResponse:
        page_target = page_url or url
        # A write interrupted by a navigation may already have reached the app: never send it twice.
        retry = idempotent if idempotent is not None else method.upper() in SAFE_METHODS
        page = await self._page_on_origin(page_target)
        if page is None:
            raise NeedsLogin(
                f"The browser was redirected away from {origin_of(page_target)}: "
                "the session is gone. Log in again on the Browser page."
            )
        request_headers = {name.lower(): value for name, value in (headers or {}).items()}
        if auth:
            host = urlsplit(url).hostname or ""
            for name, value in self._provider.capture.headers_for(host).items():
                request_headers.setdefault(name, value)
        body: str | None = None
        if json is not None:
            body = jsonlib.dumps(json)
            request_headers.setdefault("content-type", "application/json")
        elif form is not None:
            body = urlencode(form)
            request_headers.setdefault("content-type", "application/x-www-form-urlencoded")
        payload = {"url": url, "method": method.upper(), "headers": request_headers, "body": body}
        try:
            async with asyncio.timeout(FETCH_TIMEOUT_SECONDS):
                result = await self._evaluate(page, FETCH_SCRIPT, payload, retry=retry)
        except TimeoutError as exc:
            raise ConnectorError(f"{method.upper()} {urlsplit(url).path} took over {FETCH_TIMEOUT_SECONDS} s") from exc
        except PlaywrightError as exc:
            if not retry and _navigation_error(exc):
                raise ConnectorError(
                    f"{method.upper()} {urlsplit(url).path}: the page navigated while the request ran. It may have "
                    "reached the app; it was not sent again. Check the account in the app"
                ) from exc
            raise ConnectorError(f"{method.upper()} {urlsplit(url).path} failed in the browser: {_short(exc)}") from exc
        logger.info(
            "browser_fetch", method=method.upper(), host=urlsplit(url).hostname, path=urlsplit(url).path,
            status=result.get("status"),
        )  # fmt: skip
        return BrowserResponse(
            status=int(result.get("status", 0)),
            url=str(result.get("url") or url),
            text=str(result.get("text") or ""),
            headers=dict(result.get("headers") or {}),
        )

    async def run_recipe(self, recipe: Recipe, action: str, params: dict[str, str], *, origin: str) -> None:
        steps = render_steps(recipe.steps(action), params)
        support = self._recipe_support
        fixes = await support.fixes(recipe.app, action) if support is not None else {}
        await run_steps(
            await self._context(),
            steps,
            origin=origin_of(origin),
            app_name=recipe.app,
            recipe_action=action,
            params=params,
            fixes=fixes,
            support=support,
        )

    def captured_header(self, host: str, name: str) -> str | None:
        return self._provider.capture.get(host, name)

    async def cookies(self, domain: str) -> list[dict[str, Any]]:
        domain = domain.lower().lstrip(".")
        context = await self._context()
        found = []
        for cookie in await context.cookies():
            cookie_domain = str(cookie.get("domain", "")).lower().lstrip(".")
            if cookie_domain == domain or cookie_domain.endswith("." + domain):
                found.append(dict(cookie))
        return found

    async def local_storage(self, origin: str, key: str) -> str | None:
        page = await self._page_on_origin(origin)
        if page is None:
            return None
        try:
            value = await self._evaluate(page, LOCAL_STORAGE_SCRIPT, key)
        except PlaywrightError as exc:
            raise ConnectorError(f"Could not read local storage of {origin_of(origin)}: {_short(exc)}") from exc
        return value if isinstance(value, str) else None

    async def evaluate(self, origin: str, script: str, arg: Any = None) -> Any:
        page = await self._page_on_origin(origin)
        if page is None:
            raise NeedsLogin(f"The browser was redirected away from {origin_of(origin)}. Log in on the Browser page.")
        try:
            return await self._evaluate(page, script, arg)
        except PlaywrightError as exc:
            raise ConnectorError(f"Script failed on {origin_of(origin)}: {_short(exc)}") from exc


def _short(exc: BaseException) -> str:
    text = str(exc).strip()
    return text.splitlines()[0][:300] if text else exc.__class__.__name__


async def open_browser_session(
    provider: BrowserProvider | None = None, *, recipe_support: RecipeSupport | None = None
) -> CdpBrowserSession:
    """Session on the process's shared connection. Raises ``BrowserUnavailableError`` when Chromium is down.

    ``recipe_support`` (writes only) adds local fixes and AI repair to ``run_recipe``.
    """
    provider = provider or get_browser_provider()
    await provider.connect()
    return CdpBrowserSession(provider, recipe_support)
