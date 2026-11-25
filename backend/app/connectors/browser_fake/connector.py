"""Fake browser connector: reads the app's own fake panel through the real browser.

Listed only with ``DEBUG`` or ``OPEN_REVOKE_ENABLE_FAKE_CONNECTOR``, like the
``fake`` connector. It proves the whole browser path end to end: log in in
the shared Chromium (``/login`` sets a cookie), ``fetch()`` in the page with
that cookie, ``needs_login`` when the cookie is gone, the session surviving
``docker compose restart browser``. Reads go through the panel's JSON API with
``fetch()``; writes (invite, remove) click through the panel's admin page with
the click recipe ``recipe.json`` (docs/browser-recipes.md). State in Redis
(``panel_state.py``). The panel: ``app/api/dev_panel.py``.
"""

from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from app.connectors.base import (
    AuthKind,
    Capability,
    CheckResult,
    Connector,
    ConnectorContext,
    ConnectorError,
    CreateAccountRequest,
    CreatedAccount,
    RemoteAccount,
)
from app.connectors.browser_api import browser_json, raise_for_browser_error
from app.connectors.browser_fake import mapping
from app.connectors.http import check_page_limit
from app.models.enums import Integration
from app.recipes.model import config_params, load_recipe

NAME = "Fake browser panel"
# The browser container reaches the app by a network alias from compose.yaml. Not by
# the service name `app`: .app is an HSTS-preloaded TLD, so Chromium forces https://app.
DEFAULT_PANEL_URL = "http://open-revoke-app:8000/api/dev/fake-panel"
RECIPE = Path(__file__).with_name("recipe.json")


class BrowserFakeConfig(BaseModel):
    panel_url: str = Field(
        default=DEFAULT_PANEL_URL, title="Panel URL", description="Fake panel as the browser container sees it"
    )
    accounts: int = Field(default=5, ge=0, le=500, title="Number of accounts")
    page_size: int = Field(default=2, ge=1, le=100, title="Page size", description="Small pages test pagination")


type Ctx = ConnectorContext[BrowserFakeConfig]


class BrowserFakeConnector(Connector):
    key = "browser_fake"
    display_name = "Fake browser panel (development)"
    integration = Integration.BROWSER
    auth_kind = AuthKind.BROWSER_SESSION
    capabilities = frozenset({Capability.LIST_ACCOUNTS, Capability.CREATE_ACCOUNT, Capability.DELETE_ACCOUNT})
    config_schema = BrowserFakeConfig
    target_fields = ("panel_url",)
    login_url = f"{DEFAULT_PANEL_URL}/login"
    admin_url = DEFAULT_PANEL_URL

    def login_page(self, config: dict[str, Any]) -> str | None:
        return f"{str(config.get('panel_url') or DEFAULT_PANEL_URL).rstrip('/')}/login"

    async def check(self, ctx: Ctx) -> CheckResult:
        users, _ = await self._page(ctx, 1, 1)
        return CheckResult(ok=True, message=f"Logged in to the fake panel ({len(users)} user on the first page).")

    async def list_accounts(self, ctx: Ctx) -> list[RemoteAccount]:
        accounts: list[RemoteAccount] = []
        page: int | None = 1
        pages = 0
        while page is not None:
            pages += 1
            check_page_limit(pages, NAME)
            users, page = await self._page(ctx, page, ctx.config.page_size)
            accounts.extend(mapping.user_to_account(user) for user in users)
        return accounts

    async def create_account(self, ctx: Ctx, req: CreateAccountRequest) -> CreatedAccount:
        """Invites the user by clicking through the admin page, then reads the new account back."""
        assert ctx.browser is not None
        params = {**config_params(ctx.config), "email": req.email, "role": req.role or "member"}
        await ctx.browser.run_recipe(load_recipe(RECIPE), "create_account", params, origin=ctx.config.panel_url)
        email = req.email.strip().lower()
        for account in await self.list_accounts(ctx):
            if account.email == email:
                return CreatedAccount(account=account)
        raise ConnectorError(f"The invite recipe ran, but {email} is not in the fake panel's user list")

    async def delete_account(self, ctx: Ctx, account: RemoteAccount) -> None:
        """Removes the user by clicking through the admin page; the action's read-back verifies it."""
        assert ctx.browser is not None
        if not account.email:
            raise ConnectorError("The account has no e-mail, so the recipe cannot find its row")
        params = {**config_params(ctx.config), "email": account.email, "external_id": account.external_id}
        await ctx.browser.run_recipe(load_recipe(RECIPE), "delete_account", params, origin=ctx.config.panel_url)

    async def _page(self, ctx: Ctx, page: int, per_page: int) -> tuple[list[dict[str, Any]], int | None]:
        assert ctx.browser is not None
        base = ctx.config.panel_url.rstrip("/")
        url = f"{base}/users?page={page}&per_page={per_page}&count={ctx.config.accounts}"
        response = await ctx.browser.fetch(url, page_url=base)
        raise_for_browser_error(response, NAME)
        return mapping.parse_page(browser_json(response, NAME))
