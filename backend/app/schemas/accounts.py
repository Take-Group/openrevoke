import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.models.enums import AccountKind, AccountStatus, MatchMethod
from app.schemas.common import ApiModel, MoneyAmount, PersonRef
from app.schemas.people_import import FieldChange, ImportRowAction


class AccountOut(ApiModel):
    id: uuid.UUID
    app_id: uuid.UUID
    connection_id: uuid.UUID | None
    external_id: str
    email: str | None
    username: str | None
    display_name: str | None
    role: str | None
    status: AccountStatus
    kind: AccountKind
    match_method: MatchMethod
    person: PersonRef | None
    monthly_cost: MoneyAmount | None = Field(description="Per-seat price when the account is a billable seat")
    monthly_cost_converted: MoneyAmount | None = Field(description="monthly_cost in the organization currency")
    first_seen_at: datetime
    last_seen_at: datetime | None
    removed_at: datetime | None


class AccountPage(BaseModel):
    items: list[AccountOut]
    total: int


class AccountCreate(BaseModel):
    """A manual account in an app with ``integration = manual``.

    Give at least one of ``email``, ``username``, ``display_name``. Without
    ``person_id`` the account is matched to a person by e-mail.
    """

    email: str | None = Field(default=None, max_length=320)
    username: str | None = Field(default=None, max_length=320)
    display_name: str | None = Field(default=None, max_length=320)
    role: str | None = Field(default=None, max_length=100)
    status: AccountStatus = AccountStatus.ACTIVE
    kind: AccountKind | None = Field(default=None, description="Defaults to person when matched, unknown otherwise")
    person_id: uuid.UUID | None = None


class AccountUpdate(BaseModel):
    """Only the fields present in the request change.

    Setting ``person_id`` (also to null) is a manual assignment: sync never
    overrides it. ``role``, ``status`` and ``display_name`` can change only
    on accounts without a connection.
    """

    person_id: uuid.UUID | None = None
    kind: AccountKind | None = None
    role: str | None = Field(default=None, max_length=100)
    status: AccountStatus | None = None
    display_name: str | None = Field(default=None, max_length=320)


class AccountImportRow(BaseModel):
    """What one CSV row (or one pasted e-mail) does."""

    line: int = Field(description="Line in the file (the header is line 1), or the position of a pasted e-mail")
    app: str = Field(description="The app as written in the file")
    app_id: uuid.UUID | None = Field(description="Null for an app the import creates (until it is saved) or an error")
    email: str | None
    username: str | None
    display_name: str | None
    action: ImportRowAction
    account_id: uuid.UUID | None = Field(description="Existing account (update, unchanged) or the created one")
    person: PersonRef | None = Field(description="Owner: matched by e-mail for new accounts")
    changes: list[FieldChange]
    errors: list[str]


class AccountImportNewApp(BaseModel):
    name: str
    catalog_key: str | None
    app_id: uuid.UUID | None = Field(description="Set once saved; null with dry_run")


class AccountImportResult(BaseModel):
    """With ``dry_run`` nothing is saved and the counts say what would happen."""

    dry_run: bool
    created: int
    updated: int
    unchanged: int
    failed: int
    rows: list[AccountImportRow]
    new_apps: list[AccountImportNewApp] = Field(description="Apps the import creates (create_apps=true)")


class AccountsPaste(BaseModel):
    """E-mails separated by new lines, commas or semicolons; ``Name <e-mail>`` works too."""

    emails: str = Field(min_length=1, max_length=500_000)
