import uuid
from enum import StrEnum

from pydantic import BaseModel, Field

from app.schemas.common import MoneyAmount
from app.schemas.currencies import ExchangeRatesInfo


class AlertKind(StrEnum):
    LEFT_PERSON_ACTIVE_ACCOUNT = "left_person_active_account"
    UNASSIGNED_ACCOUNTS = "unassigned_accounts"
    CONNECTION_NEEDS_LOGIN = "connection_needs_login"
    CONNECTION_ERROR = "connection_error"
    ACTION_FAILED = "action_failed"
    PERSON_INACTIVE_IN_SOURCE = "person_inactive_in_source"
    DISCOVERED_SIGN_INS_AT_RISK = "discovered_sign_ins_at_risk"
    PEOPLE_WITHOUT_MANAGER = "people_without_manager"
    PROFILE_ACCESS_MISSING = "profile_access_missing"


class AlertSeverity(StrEnum):
    CRITICAL = "critical"
    WARNING = "warning"


class AlertEntityType(StrEnum):
    ACCOUNT = "account"
    APP = "app"
    CONNECTION = "connection"
    ACTION = "action"
    PERSON = "person"
    DISCOVERED_APP = "discovered_app"
    ACCESS_PROFILE = "access_profile"


class Alert(BaseModel):
    kind: AlertKind
    severity: AlertSeverity
    message: str
    entity_type: AlertEntityType
    entity_id: uuid.UUID = Field(description="The record; people_without_manager: the first of those people")
    app_id: uuid.UUID | None = Field(description="App to link to, when the alert concerns one")
    person_id: uuid.UUID | None = Field(description="Person to link to, when the alert concerns one")
    count: int | None = Field(
        description=(
            "Number of items for grouped alerts (unassigned_accounts, discovered_sign_ins_at_risk, "
            "people_without_manager, profile_access_missing)"
        )
    )


class DashboardCounts(BaseModel):
    people_active: int
    people_left: int
    apps: int
    accounts: int = Field(description="Accounts that are not removed")
    seats: int = Field(description="Billable seats in all apps")
    accounts_unassigned: int
    connections_with_problems: int = Field(description="Connections with status needs_login or error")
    actions_pending_approval: int
    actions_failed: int


class Dashboard(BaseModel):
    counts: DashboardCounts
    monthly_cost: list[MoneyAmount] = Field(description="Total monthly cost of all apps, per currency")
    monthly_cost_total: MoneyAmount | None = Field(
        description="All of monthly_cost in the organization currency; null when a currency has no rate"
    )
    exchange_rates: ExchangeRatesInfo | None = Field(description="Rates used for the conversion")
    alerts: list[Alert] = Field(description="Critical alerts first")
