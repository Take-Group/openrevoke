"""Google Workspace: Admin SDK Directory API with a service account (docs/connectors/google_workspace.md)."""

import secrets
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, Field, SecretStr, model_validator

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
    RemotePerson,
    SecretField,
)
from app.connectors.discovery import AppDiscovery, DiscoveryResult
from app.connectors.google_workspace import discovery, discovery_mapping, mapping
from app.connectors.google_workspace.auth import access_token
from app.connectors.google_workspace.scopes import SCOPE_AUDIT, SCOPE_READ, SCOPE_TOKENS, SCOPE_WRITE
from app.connectors.http import check_page_limit, json_body, raise_for_app_error
from app.models.enums import Integration

if TYPE_CHECKING:
    from datetime import datetime

API = "https://admin.googleapis.com/admin/directory/v1"
PAGE_SIZE = 500  # users.list maximum
NAME = "Google Workspace"


class GoogleWorkspaceConfig(BaseModel):
    admin_email: str = Field(
        pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$",
        title="Admin e-mail",
        description="Super admin the service account acts as, or the admin who connected with Google",
    )
    customer: str = Field(
        default="my_customer",
        title="Customer ID",
        description="Leave my_customer for the account of the admin above",
        min_length=1,
    )
    domain: str | None = Field(
        default=None, title="Domain", description="Optional: read only users of this domain instead of all domains"
    )
    service_account_json: SecretStr | None = SecretField(
        default=None,
        title="Service account key (JSON)",
        description="JSON key of a service account with domain-wide delegation. Empty when connected with Google",
        multiline=True,
    )
    oauth_client_id: str | None = Field(
        default=None,
        title="OAuth client ID",
        description='Set by "Connect with Google" on the Discovery page',
    )
    oauth_client_secret: SecretStr | None = SecretField(default=None, title="OAuth client secret")
    oauth_refresh_token: SecretStr | None = SecretField(
        default=None, title="OAuth refresh token", description='Set by "Connect with Google"'
    )

    @model_validator(mode="after")
    def _has_credentials(self) -> GoogleWorkspaceConfig:
        """A service account key, or all three OAuth values. The key wins when both are set."""
        oauth = (self.oauth_client_id, self.oauth_client_secret, self.oauth_refresh_token)
        if self.service_account_json is None and not all(oauth):
            raise ValueError("Paste a service account key, or connect with Google on the Discovery page")
        return self


type Ctx = ConnectorContext[GoogleWorkspaceConfig]


class GoogleWorkspaceConnector(Connector, AppDiscovery):
    key = "google_workspace"
    display_name = NAME
    integration = Integration.API
    auth_kind = AuthKind.GOOGLE_SERVICE_ACCOUNT
    capabilities = frozenset(
        {
            Capability.LIST_ACCOUNTS,
            Capability.LIST_PEOPLE,
            Capability.CREATE_ACCOUNT,
            Capability.DELETE_ACCOUNT,
            Capability.DISCOVER_APPS,
        }
    )
    config_schema = GoogleWorkspaceConfig
    admin_url = "https://admin.google.com/ac/users"
    delete_suspends = True
    discovery_scopes = (SCOPE_READ, SCOPE_AUDIT)
    optional_discovery_scopes = (SCOPE_TOKENS,)

    async def check(self, ctx: Ctx) -> CheckResult:
        users, _ = await self._users_page(ctx, await self._token(ctx, SCOPE_READ), None, page_size=1)
        return CheckResult(ok=True, message=f"Connected. Directory API answered ({len(users)} user on the first page).")

    async def list_accounts(self, ctx: Ctx) -> list[RemoteAccount]:
        return [mapping.user_to_account(user) for user in await self._all_users(ctx)]

    async def list_people(self, ctx: Ctx) -> list[RemotePerson]:
        return [mapping.user_to_person(user) for user in await self._all_users(ctx)]

    async def create_account(self, ctx: Ctx, req: CreateAccountRequest) -> CreatedAccount:
        if not req.first_name or not req.last_name:
            raise ConnectorError("Google Workspace needs a first and a last name to create a user")
        password = generate_temporary_password()
        body = {
            "primaryEmail": req.email,
            "name": {"givenName": req.first_name, "familyName": req.last_name},
            "password": password,
            "changePasswordAtNextLogin": True,
        }
        token = await self._token(ctx, SCOPE_WRITE)
        response = await ctx.http.post(f"{API}/users", json=body, headers=_auth(token))
        raise_for_app_error(response, NAME)
        user = json_body(response, NAME)
        return CreatedAccount(account=mapping.user_to_account(user), temporary_password=password)

    async def delete_account(self, ctx: Ctx, account: RemoteAccount) -> None:
        """Suspends the user. Never deletes: deletion removes mail and files for good."""
        token = await self._token(ctx, SCOPE_WRITE)
        response = await ctx.http.put(
            f"{API}/users/{account.external_id}", json={"suspended": True}, headers=_auth(token)
        )
        raise_for_app_error(response, NAME)

    async def discover_apps(self, ctx: Ctx, since: datetime, until: datetime) -> DiscoveryResult:
        """Sign-ins to third-party apps (audit log) plus the tokens people hold now."""
        audit_token = await discovery.audit_token(ctx)
        users = discovery.directory_users(await self._all_users(ctx))
        book = discovery_mapping.GrantBook()
        for activity in await discovery.read_activities(ctx, audit_token, "token", "authorize", since, until):
            book.add_activity(activity)
        deleted: dict[str, datetime] = {}
        for activity in await discovery.read_activities(ctx, audit_token, "admin", "DELETE_USER", since, until):
            found = discovery_mapping.deleted_user(activity)
            if found is None:
                continue
            email, at = found
            if email not in deleted or at > deleted[email]:
                deleted[email] = at  # the latest deletion of a re-created address
        note = await discovery.read_token_inventory(ctx, [user.email for user in users], book)
        notes = [note] if note else []
        if book.skipped_google:
            notes.append(f"Skipped {book.skipped_google} sign-ins to Google's own apps and devices.")
        return DiscoveryResult(
            grants=book.result(),
            directory=users,
            deleted_users=deleted,
            events_from=since,
            events_until=until,
            token_inventory=note is None,
            notes=notes,
        )

    async def _all_users(self, ctx: Ctx) -> list[dict[str, Any]]:
        token = await self._token(ctx, SCOPE_READ)
        users: list[dict[str, Any]] = []
        page_token: str | None = None
        pages = 0
        while True:
            pages += 1
            check_page_limit(pages, NAME)
            page, page_token = await self._users_page(ctx, token, page_token)
            users.extend(page)
            if not page_token:
                return users

    async def _users_page(
        self, ctx: Ctx, token: str, page_token: str | None, page_size: int = PAGE_SIZE
    ) -> tuple[list[dict[str, Any]], str | None]:
        params: dict[str, str | int] = {"maxResults": page_size, "projection": "basic", "viewType": "admin_view"}
        if ctx.config.domain:
            params["domain"] = ctx.config.domain
        else:
            params["customer"] = ctx.config.customer
        if page_token:
            params["pageToken"] = page_token
        response = await ctx.http.get(f"{API}/users", params=params, headers=_auth(token))
        raise_for_app_error(response, NAME)
        return mapping.parse_users_page(json_body(response, NAME))

    async def _token(self, ctx: Ctx, scope: str) -> str:
        return await access_token(ctx, scope)


def generate_temporary_password() -> str:
    """24 random URL-safe characters; Google accepts 8 to 100."""
    return secrets.token_urlsafe(18)


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}
