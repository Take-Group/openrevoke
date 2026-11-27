"""Claude (Team, Enterprise) through the admin's browser session (docs/connectors/claude-team.md).

claude.ai authenticates its own API with the session cookie, so a ``fetch()``
from a claude.ai tab is enough. Endpoints and payloads are NOT verified on a
real organization; they are constants here so a capture can correct them in
one place.
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
    RemoteAccount,
)
from app.connectors.browser_api import BrowserResponse, browser_json, raise_for_browser_error
from app.connectors.claude import mapping
from app.connectors.errors import ConnectorError
from app.models.enums import Integration

NAME = mapping.NAME

# --- Endpoints (not verified, see docs/connectors/claude-team.md) ------------------
ORIGIN = "https://claude.ai"
APP_PAGE = f"{ORIGIN}/"
ORGANIZATIONS = f"{ORIGIN}/api/organizations"
MEMBERS = f"{ORIGIN}/api/organizations/{{org}}/members"
MEMBER = f"{ORIGIN}/api/organizations/{{org}}/members/{{account}}"
INVITES = f"{ORIGIN}/api/organizations/{{org}}/invites"
INVITE = f"{ORIGIN}/api/organizations/{{org}}/invites/{{invite}}"
HEADERS = {"anthropic-client-platform": "web_claude_ai", "accept": "application/json"}
# Answer to /api/organizations when the session is gone.
SESSION_STATUSES = (401, 403)
DEFAULT_INVITE_ROLE = "user"


class ClaudeConfig(BaseModel):
    org_uuid: str | None = Field(
        default=None,
        title="Organization ID",
        description="Needed only when the admin account belongs to several Team organizations",
        max_length=100,
    )


type Ctx = ConnectorContext[ClaudeConfig]


class ClaudeConnector(Connector):
    key = "claude"
    display_name = "Claude (Team)"
    integration = Integration.BROWSER
    auth_kind = AuthKind.BROWSER_SESSION
    capabilities = frozenset({Capability.LIST_ACCOUNTS, Capability.CREATE_ACCOUNT, Capability.DELETE_ACCOUNT})
    config_schema = ClaudeConfig
    login_url = f"{ORIGIN}/login"
    admin_url = f"{ORIGIN}/settings/members"

    async def check(self, ctx: Ctx) -> CheckResult:
        org = await self._organization(ctx)
        members = mapping.parse_list(await self._get(ctx, MEMBERS.format(org=org["uuid"])), "members")
        return CheckResult(
            ok=True, message=f"Logged in to Claude organization {org.get('name')} ({len(members)} members)."
        )

    async def list_accounts(self, ctx: Ctx) -> list[RemoteAccount]:
        org = (await self._organization(ctx))["uuid"]
        members = mapping.parse_list(await self._get(ctx, MEMBERS.format(org=org)), "members")
        invites = mapping.parse_list(await self._get(ctx, INVITES.format(org=org)), "invites")
        accounts = [mapping.member_to_account(member) for member in members]
        accounts += [mapping.invite_to_account(invite) for invite in invites if mapping.is_pending(invite)]
        return accounts

    async def create_account(self, ctx: Ctx, req: CreateAccountRequest) -> CreatedAccount:
        org = (await self._organization(ctx))["uuid"]
        role = "admin" if req.role == "admin" else DEFAULT_INVITE_ROLE
        response = await self._request(
            ctx, INVITES.format(org=org), method="POST", json={"email_address": req.email, "role": role}
        )
        raise_for_browser_error(response, NAME)
        return CreatedAccount(account=mapping.created_invite(browser_json(response, NAME), req.email))

    async def delete_account(self, ctx: Ctx, account: RemoteAccount) -> None:
        """Removes a member from the organization, or revokes a pending invite."""
        org = (await self._organization(ctx))["uuid"]
        invite = mapping.invite_id(account.external_id)
        if invite is not None:
            url = INVITE.format(org=org, invite=invite)
        else:
            url = MEMBER.format(org=org, account=account.external_id)
        response = await self._request(ctx, url, method="DELETE")
        raise_for_browser_error(response, NAME)

    async def _organization(self, ctx: Ctx) -> dict[str, Any]:
        response = await self._request(ctx, ORGANIZATIONS)
        raise_for_browser_error(response, NAME, auth_statuses=SESSION_STATUSES)
        orgs = browser_json(response, NAME)
        if not isinstance(orgs, list):
            raise ConnectorError(f"{NAME} returned an unexpected organizations response")
        return mapping.pick_organization([org for org in orgs if isinstance(org, dict)], ctx.config.org_uuid)

    async def _get(self, ctx: Ctx, url: str) -> Any:
        response = await self._request(ctx, url)
        if response.status == 403:
            raise ConnectorError(f"{NAME} refused the member list (HTTP 403): the logged-in account is not an admin")
        raise_for_browser_error(response, NAME)
        return browser_json(response, NAME)

    async def _request(self, ctx: Ctx, url: str, *, method: str = "GET", json: Any = None) -> BrowserResponse:
        assert ctx.browser is not None
        return await ctx.browser.fetch(url, method=method, json=json, headers=HEADERS, page_url=APP_PAGE)
