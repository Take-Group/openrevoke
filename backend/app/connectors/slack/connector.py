"""Slack through the admin's browser session (docs/connectors/slack.md).

The web client keeps a token per workspace (``xoxc-...``) in local storage of
app.slack.com; the ``d`` cookie on .slack.com must go with every request. The
API runs on the workspace host, and from app.slack.com it answers CORS with
``Access-Control-Allow-Origin: *``, which blocks the cookie ("Failed to fetch",
checked 25.11.2026 on a real workspace). So the requests run in a tab
on the workspace origin (``WORKSPACE_PAGE``), same-origin, with the cookie.
``auth.test`` is verified that way; the other methods are not yet: endpoints and
payloads are constants here so a capture can correct them in one place.
"""

import asyncio
import re
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, field_validator

from app.connectors.base import (
    AuthKind,
    BillingInfo,
    Capability,
    CheckResult,
    Connector,
    ConnectorContext,
    CreateAccountRequest,
    CreatedAccount,
    RemoteAccount,
)
from app.connectors.browser_api import BrowserResponse, browser_json, raise_for_browser_error
from app.connectors.errors import ConnectorError, NeedsLogin
from app.connectors.http import check_page_limit
from app.connectors.slack import mapping
from app.models.enums import Integration
from app.recipes.model import config_params, load_recipe

NAME = mapping.NAME

# --- Endpoints (not verified, see docs/connectors/slack.md) -------------------
CLIENT_PAGE = "https://app.slack.com/client"  # tab whose local storage holds the token
LOCAL_CONFIG_KEY = "localConfig_v2"
# Light page on the workspace host that does not redirect: API calls from it are same-origin.
WORKSPACE_PAGE = "https://{workspace}.slack.com/robots.txt"
RECIPE = Path(__file__).with_name("recipe.json")  # writes click through the admin page
API_URL = "https://{workspace}.slack.com/api/{method}"
AUTH_TEST = "auth.test"
USERS_LIST = "users.list"
USERS_LOOKUP_BY_EMAIL = "users.lookupByEmail"
BILLING = "retail.getAvailablePlans"  # undocumented, read by the admin billing page
# Web API methods that only read: safe to send again after a navigation interrupted them.
READ_METHODS = frozenset({AUTH_TEST, USERS_LIST, USERS_LOOKUP_BY_EMAIL, BILLING})
PAGE_LIMIT = 200
RATE_LIMIT_RETRIES = 3
MAX_RETRY_AFTER_SECONDS = 60

WORKSPACE_PATTERN = re.compile(r"^[a-z0-9][a-z0-9-]{0,62}$")


class SlackConfig(BaseModel):
    workspace: str = Field(
        title="Workspace",
        description="Subdomain of the workspace, e.g. acme for acme.slack.com",
        min_length=1,
        max_length=63,
    )

    @field_validator("workspace", mode="before")
    @classmethod
    def _subdomain(cls, value: Any) -> Any:
        if not isinstance(value, str):
            return value
        cleaned = value.strip().lower().removeprefix("https://").removeprefix("http://").split("/")[0]
        cleaned = cleaned.removesuffix(".slack.com")
        if not WORKSPACE_PATTERN.match(cleaned):
            raise ValueError("Give the workspace subdomain, e.g. acme for acme.slack.com")
        return cleaned


type Ctx = ConnectorContext[SlackConfig]


class SlackConnector(Connector):
    key = "slack"
    display_name = NAME
    integration = Integration.BROWSER
    auth_kind = AuthKind.BROWSER_SESSION
    capabilities = frozenset(
        {Capability.LIST_ACCOUNTS, Capability.CREATE_ACCOUNT, Capability.DELETE_ACCOUNT, Capability.READ_BILLING}
    )
    config_schema = SlackConfig
    login_url = "https://slack.com/signin"
    admin_url = "https://app.slack.com/manage"

    def login_page(self, config: dict[str, Any]) -> str | None:
        workspace = config.get("workspace")
        return f"https://{workspace}.slack.com/" if workspace else self.login_url

    def browser_origins(self, config: dict[str, Any]) -> set[str]:
        return super().browser_origins(config) | {"https://app.slack.com", "https://slack.com"}

    async def check(self, ctx: Ctx) -> CheckResult:
        body = await self._call(ctx, AUTH_TEST, {})
        return CheckResult(ok=True, message=mapping.team_summary(body))

    async def list_accounts(self, ctx: Ctx) -> list[RemoteAccount]:
        accounts: list[RemoteAccount] = []
        cursor: str | None = ""
        pages = 0
        while cursor is not None:
            pages += 1
            check_page_limit(pages, NAME)
            params = {"limit": str(PAGE_LIMIT)}
            if cursor:
                params["cursor"] = cursor
            body = await self._call(ctx, USERS_LIST, params)
            for member in mapping.parse_members(body):
                account = mapping.member_to_account(member)
                if account is not None:
                    accounts.append(account)
            cursor = mapping.next_cursor(body)
        return accounts

    async def read_billing(self, ctx: Ctx) -> BillingInfo:
        """Plan, price per billed member and billed members, as the admin billing page shows them."""
        return mapping.billing_from_plans(await self._call(ctx, BILLING, {}))

    async def create_account(self, ctx: Ctx, req: CreateAccountRequest) -> CreatedAccount:
        """Invites a full member by e-mail with the click recipe (admin page, Invite People)."""
        assert ctx.browser is not None
        params = {**config_params(ctx.config), "email": req.email}
        origin = WORKSPACE_PAGE.format(workspace=ctx.config.workspace)
        await ctx.browser.run_recipe(load_recipe(RECIPE), "create_account", params, origin=origin)
        try:
            body = await self._call(ctx, USERS_LOOKUP_BY_EMAIL, {"email": req.email})
            account = mapping.member_to_account(body.get("user") or {})
        except ConnectorError:
            account = None  # invited users may not be visible yet; the next sync finds them
        if account is None:
            account = RemoteAccount(
                external_id=f"invite:{req.email.lower()}",
                email=req.email.lower(),
                display_name=None,
                username=None,
                role="member",
                status="invited",
            )
        return CreatedAccount(account=account)

    async def delete_account(self, ctx: Ctx, account: RemoteAccount) -> None:
        """Deactivates the member with the click recipe (revokes a pending invite). Slack keeps the messages."""
        if account.external_id.startswith("invite:"):
            raise ConnectorError("A pending Slack invitation cannot be revoked by Open Revoke yet")
        assert ctx.browser is not None
        if not account.email:
            raise ConnectorError("The member has no e-mail, so the recipe cannot check its row before deactivating")
        params = {**config_params(ctx.config), "email": account.email, "external_id": account.external_id}
        origin = WORKSPACE_PAGE.format(workspace=ctx.config.workspace)
        await ctx.browser.run_recipe(load_recipe(RECIPE), "delete_account", params, origin=origin)

    async def _token(self, ctx: Ctx) -> str:
        assert ctx.browser is not None
        raw = await ctx.browser.local_storage(CLIENT_PAGE, LOCAL_CONFIG_KEY)
        token = mapping.token_from_local_config(raw, ctx.config.workspace)
        if token is None:
            raise NeedsLogin(
                f"The browser is not logged in to the Slack workspace {ctx.config.workspace}. "
                "Log in on the Browser page."
            )
        return token

    async def _call(self, ctx: Ctx, method: str, params: dict[str, str]) -> dict[str, Any]:
        assert ctx.browser is not None
        token = await self._token(ctx)
        url = API_URL.format(workspace=ctx.config.workspace, method=method)
        response: BrowserResponse | None = None
        for attempt in range(RATE_LIMIT_RETRIES + 1):
            response = await ctx.browser.fetch(
                url,
                method="POST",
                form={"token": token, **params},
                auth=False,
                page_url=WORKSPACE_PAGE.format(workspace=ctx.config.workspace),
                idempotent=method in READ_METHODS,
            )
            if response.status != 429 or attempt == RATE_LIMIT_RETRIES:
                break
            await asyncio.sleep(_retry_after(response))
        assert response is not None
        raise_for_browser_error(response, NAME)
        return mapping.check_api_response(browser_json(response, NAME), method)


def _retry_after(response: BrowserResponse) -> float:
    try:
        return min(float(response.headers.get("retry-after", "5")), MAX_RETRY_AFTER_SECONDS)
    except ValueError:
        return 5.0
