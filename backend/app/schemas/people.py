import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.models.enums import PersonKind, PersonKindSource, PersonLinkSource, PersonStatus
from app.schemas.accounts import AccountOut
from app.schemas.common import ApiModel, AppRef, MoneyAmount

Name = Field(min_length=1, max_length=200)


class PersonCreate(BaseModel):
    first_name: str = Name
    last_name: str = Name
    primary_email: str = Field(min_length=3, max_length=320)
    employee_code: str | None = Field(default=None, max_length=100)
    notes: str | None = None
    aliases: list[str] = Field(default_factory=list, description="Alias e-mails used to match accounts")


class PersonUpdate(BaseModel):
    """Only the fields present in the request change.

    ``status = left`` sets ``left_at`` to now unless ``left_at`` is given;
    ``status = active`` clears it. ``aliases`` replaces the whole alias list.
    """

    first_name: str | None = Field(default=None, min_length=1, max_length=200)
    last_name: str | None = Field(default=None, min_length=1, max_length=200)
    primary_email: str | None = Field(default=None, min_length=3, max_length=320)
    employee_code: str | None = Field(default=None, max_length=100)
    notes: str | None = None
    status: PersonStatus | None = None
    left_at: datetime | None = None
    aliases: list[str] | None = None
    kind: PersonKind | None = Field(default=None, description="Person or service account; an admin's choice is kept")


class PersonListItem(ApiModel):
    id: uuid.UUID
    first_name: str
    last_name: str
    primary_email: str
    employee_code: str | None
    status: PersonStatus
    left_at: datetime | None
    kind: PersonKind = Field(description="human, or service: shared mailbox or technical account")
    kind_source: PersonKindSource = Field(description="auto: the rules set it (a sync may change it); manual: an admin")
    kind_reason: str | None = Field(description="Why the rules made it a service account")
    accounts_count: int = Field(description="Accounts that are not removed")
    apps: list[AppRef] = Field(description="Apps where the person has a not-removed account")
    monthly_cost: list[MoneyAmount] = Field(description="Sum of per-seat prices of billable accounts, per currency")
    monthly_cost_total: MoneyAmount | None = Field(
        description="All of monthly_cost in the organization currency; null when a currency has no rate"
    )
    created_at: datetime
    updated_at: datetime


class PersonPage(BaseModel):
    items: list[PersonListItem]
    total: int
    kind_counts: dict[PersonKind, int] = Field(description="Matches of the other filters per kind")


class AliasOut(ApiModel):
    id: uuid.UUID
    email: str


class PersonSourceOut(ApiModel):
    id: uuid.UUID
    source_type: PersonLinkSource
    source_id: uuid.UUID
    source_name: str
    external_id: str
    is_active: bool
    last_seen_at: datetime | None


class PersonAccountOut(AccountOut):
    app: AppRef


class PersonDetail(PersonListItem):
    notes: str | None
    aliases: list[AliasOut]
    sources: list[PersonSourceOut]
    accounts: list[PersonAccountOut] = Field(description="All accounts of the person, removed ones included")
    can_delete: bool = Field(description="True when the person has no accounts and no actions (DELETE allowed)")
