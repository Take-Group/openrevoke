"""Steps in the Google Cloud console, driven over CDP in the shared browser (Playwright ``Page``).

Every URL carries ``hl=en``: the console follows the account's language, and the selectors below
are the English labels. Each step can run again: it notices work already done (API enabled,
consent screen configured) and goes on. Labels checked on the console (English, en-US) on 23.11.2026.
"""

import asyncio
import re
from collections.abc import Awaitable, Callable
from urllib.parse import parse_qs, urlsplit

from playwright.async_api import Page, Request
from playwright.async_api import TimeoutError as PlaywrightTimeout

CONSOLE = "https://console.cloud.google.com"
NAV_TIMEOUT_MS = 60_000
UI_TIMEOUT_MS = 30_000
PROJECT_ID = re.compile(r"Project ID:\s*([a-z][a-z0-9-]{4,28}[a-z0-9])")
ACCOUNT = re.compile(r"\(([^()\s]+@[^()\s]+)\)")

type Heartbeat = Callable[[], Awaitable[None]] | Callable[[], None]


class ConsoleError(Exception):
    """A console page did not look or behave as expected. The message says which step."""


class NeedsSignInError(ConsoleError):
    """Nobody is signed in to Google in the shared browser."""


def console_url(path: str, project: str | None = None) -> str:
    query = "hl=en" + (f"&project={project}" if project else "")
    return f"{CONSOLE}{path}{'&' if '?' in path else '?'}{query}"


async def open_page(page: Page, path: str, project: str | None = None) -> None:
    # The console never goes network-idle: callers wait for the element they need.
    await page.goto(console_url(path, project), wait_until="load", timeout=NAV_TIMEOUT_MS)
    if urlsplit(page.url).hostname == "accounts.google.com":
        raise NeedsSignInError("Sign in to Google in the browser below, then start the setup again.")


async def signed_in_email(page: Page) -> str:
    await open_page(page, "/home/dashboard")
    button = page.get_by_role("button", name=re.compile(r"^Account: "))
    try:
        await button.first.wait_for(timeout=UI_TIMEOUT_MS)
    except PlaywrightTimeout as exc:
        raise NeedsSignInError("Sign in to Google in the browser below, then start the setup again.") from exc
    match = ACCOUNT.search(await button.first.get_attribute("aria-label") or "")
    if not match:
        raise ConsoleError("Could not read the signed-in Google account from the console.")
    return match.group(1).lower()


async def create_project(page: Page, name: str) -> str:
    """New project under the account's organization. Returns its ID once the console knows it."""
    await open_page(page, "/projectcreate")
    field = page.get_by_role("textbox", name="Project name")
    await field.wait_for(timeout=UI_TIMEOUT_MS)
    await field.fill(name)
    await page.wait_for_timeout(1500)  # the console proposes the project ID after typing stops
    main = page.get_by_role("main")
    match = PROJECT_ID.search(await main.inner_text())
    if not match:
        raise ConsoleError("Could not read the proposed project ID on the New Project page.")
    project_id = match.group(1)
    await main.get_by_role("button", name="Create", exact=True).click()
    for _ in range(60):  # creation takes a few seconds to a minute
        await page.wait_for_timeout(2000)
        if "projectcreate" not in page.url:
            break
    else:
        raise ConsoleError("Google Cloud did not create the project within 2 minutes.")
    await wait_for_project(page, project_id)
    return project_id


async def wait_for_project(page: Page, project_id: str) -> None:
    for _ in range(20):
        await open_page(page, "/iam-admin/settings", project_id)
        if await page.get_by_text(project_id, exact=True).count():
            return
        await page.wait_for_timeout(3000)
    raise ConsoleError(f"The project {project_id} does not show up in the console.")


async def enable_admin_api(page: Page, project_id: str) -> None:
    await open_page(page, "/apis/library/admin.googleapis.com", project_id)
    enable = page.get_by_role("button", name=re.compile(r"^enable( this API)?$", re.IGNORECASE))
    manage = page.get_by_role("button", name=re.compile(r"^manage( this API)?$", re.IGNORECASE))
    await enable.or_(manage).first.wait_for(timeout=UI_TIMEOUT_MS)
    if await manage.count():
        return  # already enabled
    await enable.click()
    try:
        await page.wait_for_url(re.compile(r"/apis/api/admin\.googleapis\.com"), timeout=120_000)
    except PlaywrightTimeout as exc:
        raise ConsoleError("Enabling the Admin SDK API did not finish within 2 minutes.") from exc


async def configure_consent_screen(page: Page, project_id: str, app_name: str, email: str) -> None:
    """Google Auth Platform wizard: app name, support e-mail, audience Internal, contact e-mail.

    Step 4 ticks "I agree to the Google API Services: User Data Policy": the panel says so before
    the admin starts the setup.
    """
    await open_page(page, "/auth/overview", project_id)
    start = page.get_by_role("link", name="Get started")
    configured = page.get_by_role("heading", name="Metrics")
    await start.or_(configured).first.wait_for(timeout=UI_TIMEOUT_MS)
    if not await start.count():
        return  # configured before
    await start.click()
    await page.get_by_role("textbox", name="App name").fill(app_name)
    await page.get_by_role("combobox", name="User support email").click()
    await page.get_by_role("option").filter(has_text=email).first.click()
    await page.get_by_role("button", name="Next").click()
    await page.get_by_role("radio", name="Internal", exact=True).check()
    await page.get_by_role("button", name="Next").click()
    await page.get_by_role("textbox", name="Text field for emails").fill(email)
    await page.keyboard.press("Enter")
    await page.get_by_role("button", name="Next").click()
    await page.get_by_role("checkbox", name=re.compile("User Data Policy")).check()
    await page.get_by_role("button", name="Continue").click()
    await page.get_by_role("button", name="Create", exact=True).click()
    try:
        await page.get_by_text("OAuth configuration created").wait_for(timeout=UI_TIMEOUT_MS)
    except PlaywrightTimeout as exc:
        raise ConsoleError("Google did not confirm the consent screen (OAuth configuration).") from exc


async def create_oauth_client(page: Page, project_id: str, name: str, redirect_uri: str) -> tuple[str, str]:
    """Web application client with one redirect URI. Returns (client ID, client secret).

    Google shows the secret only in the dialog after "Create", never again: it is read there.
    """
    await open_page(page, "/auth/clients/create", project_id)
    await _choose(page, "Application type", "Web application")
    await page.get_by_role("textbox", name="Name", exact=True).fill(name)
    redirects = page.get_by_role("group", name="Authorized redirect URIs")
    await redirects.get_by_role("button", name="Add URI").click()
    await redirects.get_by_role("textbox").last.fill(redirect_uri)
    await page.get_by_role("main").get_by_role("button", name="Create", exact=True).click()
    dialog = page.get_by_role("dialog", name="OAuth client created")
    try:
        await dialog.wait_for(timeout=UI_TIMEOUT_MS)
    except PlaywrightTimeout as exc:
        raise ConsoleError("Google did not show the new OAuth client.") from exc
    text = await dialog.inner_text()
    client_id = re.search(r"[\w-]+\.apps\.googleusercontent\.com", text)
    secret = re.search(r"\bGOCSPX-[\w-]+", text)
    if not client_id or not secret:
        raise ConsoleError("The OAuth client was created, but its ID or secret was not shown.")
    await dialog.get_by_role("button", name="OK").click()
    return client_id.group(0), secret.group(0)


async def await_redirect(page: Page, auth_url: str, redirect_uri: str, timeout: float, beat: Heartbeat) -> str:
    """Open Google's consent screen; return the redirect URL Google sends the browser to.

    The redirect URI points at the panel on the admin's computer, which this browser usually
    cannot reach. Google gets there with an HTTP redirect, and ``page.route`` does not see
    redirects, so every request of the browser context is watched instead; the page then
    shows a short note instead of the connection error.
    """
    loop = asyncio.get_running_loop()
    caught: asyncio.Future[str] = loop.create_future()

    def on_request(request: Request) -> None:
        if request.url.startswith(redirect_uri) and not caught.done():
            caught.set_result(request.url)

    page.context.on("request", on_request)
    try:
        await page.goto(auth_url, wait_until="domcontentloaded", timeout=NAV_TIMEOUT_MS)
        deadline = loop.time() + timeout
        while not caught.done():
            if loop.time() > deadline:
                raise ConsoleError("Nobody allowed access on Google's consent screen within 10 minutes.")
            result = beat()
            if asyncio.iscoroutine(result):
                await result
            await asyncio.sleep(1)
        await page.set_content(DONE_PAGE)
        return caught.result()
    finally:
        page.context.remove_listener("request", on_request)


def callback_params(url: str) -> dict[str, str | None]:
    query = parse_qs(urlsplit(url).query)
    return {name: (query.get(name) or [None])[0] for name in ("code", "state", "error")}


async def _choose(page: Page, label: str, option: str) -> None:
    """Material select: open the combobox by its label, pick the option by its text."""
    await page.get_by_role("combobox", name=label).click()
    await page.get_by_role("option", name=option, exact=True).click()


DONE_PAGE = """<!doctype html><html><body style="font:16px system-ui;padding:48px">
<h2>Google access granted</h2><p>Open Revoke is checking access and importing people. Go back to the panel.</p>
</body></html>"""
