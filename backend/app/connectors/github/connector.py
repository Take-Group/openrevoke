"""GitHub: members and pending invitations of one organization (docs/connectors/github.md)."""

from typing import Any

from pydantic import BaseModel, Field, SecretStr

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
    SecretField,
)
from app.connectors.github import mapping
from app.connectors.http import check_page_limit, json_body, raise_for_app_error
from app.models.enums import Integration

NAME = "GitHub"
PAGE_SIZE = 100  # GitHub maximum for per_page
API_VERSION = "2022-11-28"


class GitHubConfig(BaseModel):
    org: str = Field(
        title="Organization", description="Organization login, as in github.com/<org>", min_length=1, max_length=100
    )
    api_url: str = Field(
        default="https://api.github.com",
        title="API URL",
        description="Change only for GitHub Enterprise Server, e.g. https://github.example.com/api/v3",
    )
    token: SecretStr = SecretField(
        title="Access token",
        description="Token with read:org (reads); admin:org is needed for invitations and removals later",
    )


type Ctx = ConnectorContext[GitHubConfig]


class GitHubConnector(Connector):
    key = "github"
    display_name = NAME
    integration = Integration.API
    auth_kind = AuthKind.API_TOKEN
    capabilities = frozenset({Capability.LIST_ACCOUNTS, Capability.CREATE_ACCOUNT, Capability.DELETE_ACCOUNT})
    config_schema = GitHubConfig
    admin_url = "https://github.com/orgs"

    async def check(self, ctx: Ctx) -> CheckResult:
        response = await ctx.http.get(_url(ctx, f"/orgs/{ctx.config.org}"), headers=_headers(ctx))
        raise_for_app_error(response, NAME)
        org = json_body(response, NAME)
        members = await ctx.http.get(
            _url(ctx, f"/orgs/{ctx.config.org}/members"), params={"per_page": 1}, headers=_headers(ctx)
        )
        raise_for_app_error(members, NAME)
        login = org.get("login") if isinstance(org, dict) else ctx.config.org
        return CheckResult(ok=True, message=f"Connected to organization {login}.")

    async def list_accounts(self, ctx: Ctx) -> list[RemoteAccount]:
        org = ctx.config.org
        members = await self._all_pages(ctx, f"/orgs/{org}/members", {"role": "all"}, "members")
        admins = await self._all_pages(ctx, f"/orgs/{org}/members", {"role": "admin"}, "members")
        invitations = await self._all_pages(ctx, f"/orgs/{org}/invitations", {}, "invitations")
        admin_ids = {str(admin.get("id")) for admin in admins}
        accounts = [mapping.member_to_account(member, admin_ids) for member in members]
        accounts += [mapping.invitation_to_account(invitation) for invitation in invitations]
        return accounts

    async def create_account(self, ctx: Ctx, req: CreateAccountRequest) -> CreatedAccount:
        role = "admin" if req.role == "admin" else "direct_member"
        response = await ctx.http.post(
            _url(ctx, f"/orgs/{ctx.config.org}/invitations"),
            json={"email": req.email, "role": role},
            headers=_headers(ctx),
        )
        raise_for_app_error(response, NAME)
        return CreatedAccount(account=mapping.invitation_to_account(json_body(response, NAME)))

    async def delete_account(self, ctx: Ctx, account: RemoteAccount) -> None:
        """Removes a member from the organization, or cancels a pending invitation."""
        invitation = mapping.invitation_id(account.external_id)
        if invitation is not None:
            path = f"/orgs/{ctx.config.org}/invitations/{invitation}"
        elif account.username:
            path = f"/orgs/{ctx.config.org}/members/{account.username}"
        else:
            raise ConnectorError("A GitHub member account needs a login to be removed")
        response = await ctx.http.delete(_url(ctx, path), headers=_headers(ctx))
        raise_for_app_error(response, NAME)

    async def _all_pages(self, ctx: Ctx, path: str, params: dict[str, Any], what: str) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        url: str | None = _url(ctx, path)
        query: dict[str, Any] | None = {**params, "per_page": PAGE_SIZE}
        pages = 0
        while url:
            pages += 1
            check_page_limit(pages, NAME)
            # The "next" URL from the Link header already carries the query string.
            response = await ctx.http.get(url, params=query, headers=_headers(ctx))
            raise_for_app_error(response, NAME)
            items.extend(mapping.parse_list(json_body(response, NAME), what))
            url = mapping.next_page_url(response.links)
            query = None
        return items


def _url(ctx: Ctx, path: str) -> str:
    return ctx.config.api_url.rstrip("/") + path


def _headers(ctx: Ctx) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {ctx.config.token.get_secret_value()}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": API_VERSION,
    }
