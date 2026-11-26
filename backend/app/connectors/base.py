"""Connector interface and the types connectors return.

A connector talks to one SaaS app. It never writes to the database: it
returns data, the sync service stores it. Rules every connector follows:

- missing session or rejected credentials raise ``NeedsLogin``,
- a list is complete or the call raises (``IncompleteListError``), because a
  partial list would look like mass removal of accounts,
- parsing of responses lives in pure functions in ``<key>/mapping.py``.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import StrEnum
from typing import TYPE_CHECKING, Any, ClassVar, Literal
from urllib.parse import urlsplit

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from datetime import date, datetime
    from decimal import Decimal

    import httpx

    from app.connectors.browser_api import BrowserSession
    from app.models.enums import Integration


class Capability(StrEnum):
    LIST_ACCOUNTS = "list_accounts"
    CREATE_ACCOUNT = "create_account"
    DELETE_ACCOUNT = "delete_account"
    LIST_PEOPLE = "list_people"  # the connector can be a people source
    DISCOVER_APPS = "discover_apps"  # sign-ins to third-party apps (app.connectors.discovery)
    READ_BILLING = "read_billing"  # plan and price from the app's own billing


class AuthKind(StrEnum):
    API_TOKEN = "api_token"
    GOOGLE_SERVICE_ACCOUNT = "google_service_account"
    SCIM_TOKEN = "scim_token"
    BROWSER_SESSION = "browser_session"


RemoteStatus = Literal["active", "invited", "suspended"]


@dataclass
class RemoteAccount:
    external_id: str
    email: str | None
    display_name: str | None
    username: str | None
    role: str | None
    status: RemoteStatus
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class RemotePerson:
    """A person from a people source (``Capability.LIST_PEOPLE``)."""

    external_id: str
    email: str
    aliases: list[str]
    first_name: str | None
    last_name: str | None
    employee_code: str | None
    active: bool
    raw: dict[str, Any] = field(default_factory=dict)
    # For telling service accounts apart (app.services.person_kind); None when the source has no data.
    last_sign_in_at: datetime | None = None
    created_at: datetime | None = None
    # Org data. ``manager_email`` is resolved to a person after the whole list is stored
    # (``app.services.people_sync``); None means the source names no manager.
    manager_email: str | None = None
    department: str | None = None
    job_title: str | None = None


@dataclass
class BillingInfo:
    """What the app's own billing says it charges. Amounts are in ``currency``, per ``billing_period``.

    ``pricing_model`` is ``per_seat`` (``unit_amount`` per billed seat) or ``flat`` (``unit_amount`` for the
    whole plan). ``billed_seats`` and ``total_amount`` are what the app bills now, when it says so.
    """

    plan: str | None
    pricing_model: Literal["per_seat", "flat"]
    unit_amount: Decimal
    currency: str
    billing_period: Literal["monthly", "yearly"]
    billed_seats: int | None = None
    total_amount: Decimal | None = None
    renews_on: date | None = None
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class CreateAccountRequest:
    email: str
    first_name: str | None = None
    last_name: str | None = None
    role: str | None = None


@dataclass
class CreatedAccount:
    """Result of ``create_account``.

    ``temporary_password`` is shown to the admin once (Google Workspace). It
    must never be stored in ``account.raw`` or logged.
    """

    account: RemoteAccount
    temporary_password: str | None = None


@dataclass
class CheckResult:
    ok: bool
    message: str | None = None


class ConnectorError(Exception):
    """The app returned an error or data the connector cannot use."""


class NeedsLogin(ConnectorError):  # noqa: N818 - public name in the connector interface
    """No browser session, or the app rejected the credentials (401).

    Sync stops with status ``needs_login`` and leaves accounts as they are.
    """


class IncompleteListError(ConnectorError):
    """The connector could not read the full list (pagination broke off)."""


@dataclass
class ConnectorContext[ConfigT: BaseModel]:
    """What a connector gets for one call.

    ``config`` is the parsed ``config_schema`` with secrets filled in (secret
    fields are ``SecretStr``). ``secrets`` holds the same secrets as plain
    strings. ``http`` has a timeout and request logging. ``browser`` is the
    shared browser session for connectors with ``AuthKind.BROWSER_SESSION``
    (``app/connectors/browser_api.py``), ``None`` for the others.
    """

    config: ConfigT
    secrets: dict[str, str]
    http: httpx.AsyncClient
    browser: BrowserSession | None = None


SECRET_MARK = "secret"


def SecretField(*, title: str, description: str | None = None, multiline: bool = False, **kwargs: Any) -> Any:  # noqa: N802
    """A config field the UI shows as a password input and the API never returns.

    The JSON schema of the field gets ``"secret": true`` (plus ``format:
    password`` and ``writeOnly`` from ``SecretStr``). ``multiline`` adds
    ``"x-multiline": true`` for values like a service account JSON.
    """
    extra: dict[str, Any] = {SECRET_MARK: True}
    if multiline:
        extra["x-multiline"] = True
    return Field(title=title, description=description, json_schema_extra=extra, **kwargs)


def secret_field_names(model: type[BaseModel]) -> list[str]:
    names = []
    for name, info in model.model_fields.items():
        extra = info.json_schema_extra
        if isinstance(extra, dict) and extra.get(SECRET_MARK):
            names.append(name)
    return names


class Connector(ABC):
    """Base class of every connector. Subclasses set the class attributes.

    ``create_account``, ``delete_account`` and ``list_people`` are optional:
    a connector implements those listed in ``capabilities``.
    ``ExecuteActionWorkflow`` calls the write methods after approval and
    confirms each write by reading ``list_accounts`` again.
    """

    key: ClassVar[str]
    display_name: ClassVar[str]
    integration: ClassVar[Integration]
    auth_kind: ClassVar[AuthKind]
    capabilities: ClassVar[frozenset[Capability]]
    config_schema: ClassVar[type[BaseModel]]
    login_url: ClassVar[str | None] = None
    admin_url: ClassVar[str | None] = None
    # True when ``delete_account`` suspends instead of deleting (Google Workspace). The UI says "Suspend".
    delete_suspends: ClassVar[bool] = False
    # Config fields that say which organisation the writes go to. A change in any of them turns
    # writes off and needs a new successful sync. None means every config field.
    target_fields: ClassVar[tuple[str, ...] | None] = None

    @classmethod
    def target_of(cls, config: dict) -> dict:
        fields = cls.target_fields if cls.target_fields is not None else tuple(config)
        return {name: config.get(name) for name in fields}

    @abstractmethod
    async def check(self, ctx: ConnectorContext) -> CheckResult: ...

    @abstractmethod
    async def list_accounts(self, ctx: ConnectorContext) -> list[RemoteAccount]: ...

    async def create_account(self, ctx: ConnectorContext, req: CreateAccountRequest) -> CreatedAccount:
        raise ConnectorError(f"{self.display_name} connector cannot create accounts")

    async def delete_account(self, ctx: ConnectorContext, account: RemoteAccount) -> None:
        raise ConnectorError(f"{self.display_name} connector cannot delete accounts")

    async def list_people(self, ctx: ConnectorContext) -> list[RemotePerson]:
        raise ConnectorError(f"{self.display_name} connector is not a people source")

    async def read_billing(self, ctx: ConnectorContext) -> BillingInfo:
        raise ConnectorError(f"{self.display_name} connector cannot read billing")

    def login_page(self, config: dict[str, Any]) -> str | None:
        """Page the admin opens to log in (browser connectors). ``config`` is the stored config, no secrets."""
        return self.login_url

    def browser_origins(self, config: dict[str, Any]) -> set[str]:
        """Origins (``https://host``) of this app's tabs, to tell which open tab belongs to which app."""
        return {origin for url in (self.login_page(config), self.admin_url) if url and (origin := _origin(url))}

    def supports(self, capability: Capability) -> bool:
        return capability in self.capabilities

    @classmethod
    def secret_fields(cls) -> list[str]:
        return secret_field_names(cls.config_schema)

    @classmethod
    def form_schema(cls) -> dict[str, Any]:
        """JSON schema of the connection form: config and secret fields together."""
        return cls.config_schema.model_json_schema()


def _origin(url: str) -> str:
    parts = urlsplit(url)
    return f"{parts.scheme}://{parts.netloc}".lower() if parts.scheme in ("http", "https") and parts.netloc else ""
