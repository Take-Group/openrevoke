import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.models.enums import AccountKind, AccountStatus, MatchMethod
from app.schemas.common import ApiModel, MoneyAmount, PersonRef


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
