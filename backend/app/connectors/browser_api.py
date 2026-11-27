"""What browser connectors see of the shared browser.

``BrowserSession`` is the only browser API a connector uses. The real one
(``app/browser/session.py``) runs every request with ``fetch()`` inside a tab
of the panel, so the admin's cookies and origin come along. Tests pass a fake
that implements the same protocol.
"""

import json
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Protocol
from urllib.parse import urlsplit

from app.connectors.errors import ConnectorError, NeedsLogin

if TYPE_CHECKING:
    from app.recipes.model import Recipe


@dataclass
class BrowserResponse:
    """Response of a ``fetch()`` run in the page. ``text`` is the raw body."""

    status: int
    url: str
    text: str = ""
    headers: dict[str, str] = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return 200 <= self.status < 300

    def json(self) -> Any:
        return json.loads(self.text)


class BrowserUnavailableError(ConnectorError):
    """The browser container does not answer. Not a login problem: sync ends with an error."""


class BrowserSession(Protocol):
    async def open(self, url: str, *, bring_to_front: bool = False) -> str:
        """Find a tab on the origin of ``url`` or open ``url`` in a new tab. Returns the tab's URL."""
        ...

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
        """Run ``fetch(url)`` with ``credentials: "include"`` in a tab.

        The tab is the one on ``page_url``'s origin (default: ``url``'s origin),
        opened when missing. ``json`` or ``form`` set the body and its content
        type. ``auth=True`` adds the auth headers the panel itself last sent to
        this host (``captured_header``). A tab that ends up on another origin
        (redirect to a login page) raises ``NeedsLogin``. ``idempotent`` says whether the
        request may be sent again after the page navigated mid-request; default: only
        GET, HEAD and OPTIONS. A write is never repeated (it raises ``ConnectorError``).
        """
        ...

    async def run_recipe(self, recipe: Recipe, action: str, params: dict[str, str], *, origin: str) -> None:
        """Run the ``action`` steps of a click recipe in a new tab, closed afterwards (docs/browser-recipes.md).

        ``params`` fill ``{{...}}``; a missing one raises ``RecipeError`` before any click. A ``goto``
        that leaves ``origin`` raises ``NeedsLogin``; a step without a single matching element raises
        ``RecipeStepError`` naming the step (with a screenshot). During a write the session may try
        local fixes and AI repair first (``app/recipes/repair.py``). Success only means every step
        ran: verify by reading.
        """
        ...

    def captured_header(self, host: str, name: str) -> str | None:
        """Last value of an auth header (authorization, x-csrf-token...) the panel sent to ``host``."""
        ...

    async def cookies(self, domain: str) -> list[dict[str, Any]]:
        """Cookies of ``domain`` and its subdomains."""
        ...

    async def local_storage(self, origin: str, key: str) -> str | None:
        """``localStorage[key]`` on ``origin``; ``None`` when missing or the tab left the origin."""
        ...

    async def evaluate(self, origin: str, script: str, arg: Any = None) -> Any:
        """Run a JS function expression (``"(arg) => ..."``) in the tab on ``origin``."""
        ...


def raise_for_browser_error(response: BrowserResponse, app_name: str, auth_statuses: tuple[int, ...] = (401,)) -> None:
    """Rejected session raises ``NeedsLogin``, any other error status ``ConnectorError``."""
    if response.ok:
        return
    detail = short_body(response)
    if response.status in auth_statuses:
        raise NeedsLogin(
            f"{app_name} rejected the browser session (HTTP {response.status}). "
            f"Log in again on the Browser page.{detail}"
        )
    raise ConnectorError(f"{app_name} returned HTTP {response.status} for {_path(response.url)}.{detail}")


def browser_json(response: BrowserResponse, app_name: str) -> Any:
    try:
        return response.json()
    except ValueError as exc:
        hint = ""
        if response.text.lstrip().startswith("<"):
            hint = " It returned an HTML page: a login page or bot protection (CAPTCHA) in the browser."
        raise ConnectorError(f"{app_name} returned a response that is not JSON.{hint}") from exc


def short_body(response: BrowserResponse) -> str:
    text = response.text.strip().replace("\n", " ")
    if not text:
        return ""
    if text.startswith("<"):
        return " The app answered with an HTML page (a login page or bot protection)."
    return f" Response: {text[:300]}"


def _path(url: str) -> str:
    return urlsplit(url).path or "/"
