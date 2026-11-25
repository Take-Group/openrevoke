"""ChatGPT (Team, Business, Enterprise) through the admin's browser session (docs/connectors/chatgpt.md).

The web app trades its session cookie for a short-lived access token at
``/api/auth/session`` and calls ``/backend-api`` with it as a Bearer token.
The connector does the same from a chatgpt.com tab. chatgpt.com sits behind
bot protection (Cloudflare); an HTML answer instead of JSON ends the sync with
an error that says so. Endpoints and payloads are NOT verified on a real
workspace; they are constants here so a capture can correct them in one place.
"""

from typing import Any

from pydantic import BaseModel, Field

from app.connectors.base import (
    AuthKind,
    Capability,
    CheckResult,
    Connector,
    ConnectorContext,
    CreateAccountRequest,
    CreatedAccount,
    IncompleteListError,
    RemoteAccount,
)
from app.connectors.browser_api import BrowserResponse, browser_json, raise_for_browser_error
from app.connectors.chatgpt import mapping
from app.connectors.http import check_page_limit
from app.models.enums import Integration

NAME = mapping.NAME

# --- Endpoints (not verified, see docs/connectors/chatgpt.md) -----------------
ORIGIN = "https://chatgpt.com"
APP_PAGE = f"{ORIGIN}/"
SESSION = f"{ORIGIN}/api/auth/session"
ACCOUNTS_CHECK = f"{ORIGIN}/backend-api/accounts/check/v4-2023-04-27"
USERS = f"{ORIGIN}/backend-api/accounts/{{account}}/users"
USER = f"{ORIGIN}/backend-api/accounts/{{account}}/users/{{user}}"
INVITES = f"{ORIGIN}/backend-api/accounts/{{account}}/invites"
ACCOUNT_HEADER = "chatgpt-account-id"
PAGE_SIZE = 100
DEFAULT_INVITE_ROLE = "standard-user"


class ChatGptConfig(BaseModel):
    account_id: str | None = Field(
        default=None,
        title="Workspace ID",
        description="Needed only when the admin account belongs to several workspaces",
        max_length=100,
    )


type Ctx = ConnectorContext[ChatGptConfig]


class ChatGptConnector(Connector):
    key = "chatgpt"
    display_name = "ChatGPT (Team)"
    integration = Integration.BROWSER
    auth_kind = AuthKind.BROWSER_SESSION
    capabilities = frozenset({Capability.LIST_ACCOUNTS, Capability.CREATE_ACCOUNT, Capability.DELETE_ACCOUNT})
    config_schema = ChatGptConfig
    login_url = f"{ORIGIN}/auth/login"
    admin_url = f"{ORIGIN}/admin"

    async def check(self, ctx: Ctx) -> CheckResult:
        token, account = await self._workspace(ctx)
        _, total = await self._page(ctx, token, account, USERS.format(account=account), 0, 1, "users")
        count = f"{total} members" if total is not None else "members readable"
        return CheckResult(ok=True, message=f"Logged in to ChatGPT workspace {account} ({count}).")

    async def list_accounts(self, ctx: Ctx) -> list[RemoteAccount]:
        token, account = await self._workspace(ctx)
        users = await self._all(ctx, token, account, USERS.format(account=account), "users")
        invites = await self._all(ctx, token, account, INVITES.format(account=account), "invites")
        return [mapping.user_to_account(user) for user in users] + [
            mapping.invite_to_account(invite) for invite in invites
        ]

    async def create_account(self, ctx: Ctx, req: CreateAccountRequest) -> CreatedAccount:
        token, account = await self._workspace(ctx)
        role = "account-admin" if req.role == "admin" else DEFAULT_INVITE_ROLE
        body = {"email_addresses": [req.email], "role": role, "resend_emails": True}
        response = await self._request(ctx, token, account, INVITES.format(account=account), "POST", body)
        raise_for_browser_error(response, NAME)
        return CreatedAccount(account=mapping.created_invite(browser_json(response, NAME), req.email))

    async def delete_account(self, ctx: Ctx, account: RemoteAccount) -> None:
        """Removes a member from the workspace, or revokes a pending invite (by e-mail)."""
        token, workspace = await self._workspace(ctx)
        if mapping.is_invite(account.external_id):
            body = {"email_address": account.email}
            response = await self._request(ctx, token, workspace, INVITES.format(account=workspace), "DELETE", body)
        else:
            url = USER.format(account=workspace, user=account.external_id)
            response = await self._request(ctx, token, workspace, url, "DELETE")
        raise_for_browser_error(response, NAME)

    async def _workspace(self, ctx: Ctx) -> tuple[str, str]:
        """Access token and workspace account id."""
        assert ctx.browser is not None
        response = await ctx.browser.fetch(SESSION, auth=False, page_url=APP_PAGE)
        raise_for_browser_error(response, NAME, auth_statuses=(401, 403))
        token = mapping.access_token(browser_json(response, NAME))
        if ctx.config.account_id:
            return token, ctx.config.account_id
        check = await self._request(ctx, token, None, ACCOUNTS_CHECK, "GET")
        raise_for_browser_error(check, NAME)
        return token, mapping.pick_workspace(mapping.workspaces(browser_json(check, NAME)), None)

    async def _all(self, ctx: Ctx, token: str, account: str, url: str, what: str) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        offset: int | None = 0
        pages = 0
        previous: list[dict[str, Any]] | None = None
        while offset is not None:
            pages += 1
            check_page_limit(pages, NAME)
            page, total = await self._page(ctx, token, account, url, offset, PAGE_SIZE, what)
            if page and page == previous:
                raise IncompleteListError(f"{NAME} returned the same {what} again; it ignores the offset")
            previous = page
            items.extend(page)
            offset = mapping.next_offset(offset, page, total, PAGE_SIZE, what)
        return items

    async def _page(
        self, ctx: Ctx, token: str, account: str, url: str, offset: int, limit: int, what: str
    ) -> tuple[list[dict[str, Any]], int | None]:
        response = await self._request(ctx, token, account, f"{url}?offset={offset}&limit={limit}", "GET")
        raise_for_browser_error(response, NAME)
        return mapping.parse_page(browser_json(response, NAME), what)

    async def _request(
        self, ctx: Ctx, token: str, account: str | None, url: str, method: str, json: Any = None
    ) -> BrowserResponse:
        assert ctx.browser is not None
        headers = {"authorization": f"Bearer {token}", "accept": "application/json"}
        if account:
            headers[ACCOUNT_HEADER] = account
        return await ctx.browser.fetch(url, method=method, json=json, headers=headers, auth=False, page_url=APP_PAGE)
