"""Fake connector with deterministic data, for development and end-to-end checks.

Listed only when ``DEBUG`` or ``OPEN_REVOKE_ENABLE_FAKE_CONNECTOR`` is true.
It makes no network calls. ``mode`` simulates the states a real app can be in.
Writes (create, delete) are kept in Redis (``state.py``), so verification and
the next sync read them back. ``write_mode = ignore`` accepts a write and
changes nothing, which makes verification fail.
"""

import secrets
from typing import TYPE_CHECKING, Literal

from pydantic import BaseModel, Field, SecretStr

from app.connectors.base import (
    AuthKind,
    Capability,
    CheckResult,
    Connector,
    ConnectorContext,
    CreateAccountRequest,
    CreatedAccount,
    RemoteAccount,
    RemotePerson,
    SecretField,
)
from app.connectors.discovery import AppDiscovery, DiscoveryResult
from app.connectors.errors import ConnectorError, NeedsLogin
from app.connectors.fake import mapping, state
from app.connectors.fake.discovery import fake_discovery
from app.models.enums import Integration

if TYPE_CHECKING:
    from datetime import datetime


class FakeConfig(BaseModel):
    domain: str = Field(default="example.com", title="E-mail domain", min_length=3)
    accounts: int = Field(default=5, ge=0, le=1000, title="Number of accounts")
    mode: Literal["ok", "needs_login", "error"] = Field(
        default="ok", title="Mode", description="needs_login and error simulate a broken app"
    )
    token: SecretStr = SecretField(title="Token", description="Any value. Tests that secrets stay hidden")
    write_mode: Literal["apply", "ignore"] = Field(
        default="apply", title="Writes", description="ignore answers OK but changes nothing (verification fails)"
    )
    temporary_password: bool = Field(
        default=True, title="Temporary password", description="Create returns a one-time password, like Google"
    )


type Ctx = ConnectorContext[FakeConfig]


class FakeConnector(Connector, AppDiscovery):
    key = "fake"
    display_name = "Fake app (development)"
    integration = Integration.API
    auth_kind = AuthKind.API_TOKEN
    capabilities = frozenset(
        {
            Capability.LIST_ACCOUNTS,
            Capability.LIST_PEOPLE,
            Capability.CREATE_ACCOUNT,
            Capability.DELETE_ACCOUNT,
            Capability.DISCOVER_APPS,
        }
    )
    config_schema = FakeConfig
    target_fields = ("domain",)

    async def check(self, ctx: Ctx) -> CheckResult:
        self._raise_for_mode(ctx)
        return CheckResult(ok=True, message=f"Fake app with {ctx.config.accounts} accounts.")

    async def list_accounts(self, ctx: Ctx) -> list[RemoteAccount]:
        self._raise_for_mode(ctx)
        return await state.apply_state(ctx.config.domain, mapping.fake_accounts(ctx.config.domain, ctx.config.accounts))

    async def create_account(self, ctx: Ctx, req: CreateAccountRequest) -> CreatedAccount:
        self._raise_for_mode(ctx)
        email = req.email.lower()
        if any(account.email == email for account in await self.list_accounts(ctx)):
            raise ConnectorError(f"Fake app: {email} already has an account")
        account = mapping.created_account(email, req.first_name, req.last_name, req.role)
        if ctx.config.write_mode == "apply":
            await state.add_created(ctx.config.domain, account)
        password = secrets.token_urlsafe(12) if ctx.config.temporary_password else None
        return CreatedAccount(account=account, temporary_password=password)

    async def delete_account(self, ctx: Ctx, account: RemoteAccount) -> None:
        self._raise_for_mode(ctx)
        if account.external_id not in {item.external_id for item in await self.list_accounts(ctx)}:
            raise ConnectorError(f"Fake app: no account {account.external_id}")
        if ctx.config.write_mode == "apply":
            await state.mark_deleted(ctx.config.domain, account.external_id)

    async def list_people(self, ctx: Ctx) -> list[RemotePerson]:
        self._raise_for_mode(ctx)
        return mapping.fake_people(ctx.config.domain, ctx.config.accounts)

    async def discover_apps(self, ctx: Ctx, since: datetime, until: datetime) -> DiscoveryResult:
        self._raise_for_mode(ctx)
        return fake_discovery(ctx.config.domain, ctx.config.accounts, since, until)

    def _raise_for_mode(self, ctx: Ctx) -> None:
        if ctx.config.mode == "needs_login":
            raise NeedsLogin("Fake app: the session expired (mode needs_login)")
        if ctx.config.mode == "error":
            raise ConnectorError("Fake app: simulated failure (mode error)")
