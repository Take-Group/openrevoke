"""Generic SCIM 2.0 client: works with any app that exposes /Users (docs/connectors/scim.md)."""

from typing import Any, Literal

from pydantic import BaseModel, Field, SecretStr

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
    SecretField,
)
from app.connectors.http import check_page_limit, json_body, raise_for_app_error
from app.connectors.scim import mapping
from app.models.enums import Integration

NAME = "SCIM server"
SCIM_JSON = "application/scim+json"


class ScimConfig(BaseModel):
    base_url: str = Field(
        title="SCIM base URL",
        description="Address that ends before /Users, e.g. https://app.example.com/scim/v2",
        pattern=r"^https?://\S+$",
    )
    user_filter: str | None = Field(
        default=None,
        title="User filter",
        description='Optional SCIM filter for GET /Users, e.g. userName sw "a". Users outside it count as removed',
    )
    delete_mode: Literal["deactivate", "delete"] = Field(
        default="deactivate",
        title="Removal",
        description="deactivate sets active=false (PATCH); delete calls DELETE /Users/{id}",
    )
    page_size: int = Field(default=100, ge=1, le=1000, title="Page size", description="count per GET /Users call")
    token: SecretStr = SecretField(title="Bearer token", description="SCIM token from the app's admin settings")


type Ctx = ConnectorContext[ScimConfig]


class ScimConnector(Connector):
    key = "scim"
    display_name = "SCIM 2.0"
    integration = Integration.SCIM
    auth_kind = AuthKind.SCIM_TOKEN
    capabilities = frozenset({Capability.LIST_ACCOUNTS, Capability.CREATE_ACCOUNT, Capability.DELETE_ACCOUNT})
    config_schema = ScimConfig

    async def check(self, ctx: Ctx) -> CheckResult:
        page = await self._page(ctx, start_index=1, count=1)
        return CheckResult(ok=True, message=f"Connected. The server reports {page.total_results} users.")

    async def list_accounts(self, ctx: Ctx) -> list[RemoteAccount]:
        users: dict[str, dict[str, Any]] = {}
        start_index = 1
        pages = 0
        while True:
            pages += 1
            check_page_limit(pages, NAME)
            page = await self._page(ctx, start_index=start_index, count=ctx.config.page_size)
            new = [user for user in page.resources if str(user.get("id")) not in users]
            if page.resources and not new:
                raise IncompleteListError("The SCIM server returned the same users again; it ignores startIndex")
            users.update({str(user.get("id")): user for user in page.resources})
            start_index += len(page.resources)
            if len(users) >= page.total_results:
                break
            if not page.resources:
                raise IncompleteListError(
                    f"The SCIM server reported {page.total_results} users but returned {len(users)}"
                )
        return [mapping.user_to_account(user) for user in users.values()]

    async def create_account(self, ctx: Ctx, req: CreateAccountRequest) -> CreatedAccount:
        response = await ctx.http.post(
            _url(ctx, "/Users"),
            json=mapping.create_user_body(req.email, req.first_name, req.last_name),
            headers=_headers(ctx),
        )
        raise_for_app_error(response, NAME)
        return CreatedAccount(account=mapping.user_to_account(json_body(response, NAME)))

    async def delete_account(self, ctx: Ctx, account: RemoteAccount) -> None:
        url = _url(ctx, f"/Users/{account.external_id}")
        if ctx.config.delete_mode == "delete":
            response = await ctx.http.delete(url, headers=_headers(ctx))
        else:
            response = await ctx.http.patch(url, json=mapping.deactivate_body(), headers=_headers(ctx))
        raise_for_app_error(response, NAME)

    async def _page(self, ctx: Ctx, *, start_index: int, count: int) -> mapping.ListPage:
        params: dict[str, str | int] = {"startIndex": start_index, "count": count}
        if ctx.config.user_filter:
            params["filter"] = ctx.config.user_filter
        response = await ctx.http.get(_url(ctx, "/Users"), params=params, headers=_headers(ctx))
        raise_for_app_error(response, NAME)
        return mapping.parse_list_response(json_body(response, NAME))


def _url(ctx: Ctx, path: str) -> str:
    return ctx.config.base_url.rstrip("/") + path


def _headers(ctx: Ctx) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {ctx.config.token.get_secret_value()}",
        "Accept": f"{SCIM_JSON}, application/json",
        "Content-Type": SCIM_JSON,
    }
