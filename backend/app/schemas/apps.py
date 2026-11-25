import uuid
from datetime import date, datetime

from pydantic import BaseModel, Field

from app.models.enums import BillingPeriod, ConnectionStatus, Integration, PricingModel, SelfServicePolicy
from app.schemas.actions import WriteMode
from app.schemas.common import ApiModel, Currency, Money, MoneyAmount, MoneyInput
from app.schemas.connections import ConnectionOut


class PriceIn(BaseModel):
    amount: MoneyInput = Field(description="Price of one seat (per_seat) or of the whole plan (flat)")
    currency: Currency
    billing_period: BillingPeriod = BillingPeriod.MONTHLY


class PriceOut(BaseModel):
    amount: Money
    currency: str
    billing_period: BillingPeriod


class AppCreate(BaseModel):
    """``price`` is required unless ``pricing_model`` is free, and must be null when it is."""

    name: str = Field(min_length=1, max_length=200)
    slug: str | None = Field(
        default=None, max_length=100, pattern=r"^[a-z0-9]+(-[a-z0-9]+)*$", description="Generated from name if empty"
    )
    admin_url: str | None = Field(default=None, max_length=2000)
    integration: Integration = Integration.MANUAL
    pricing_model: PricingModel = PricingModel.FREE
    price: PriceIn | None = None
    notes: str | None = None
    self_service: SelfServicePolicy = SelfServicePolicy.APPROVAL


class AppUpdate(BaseModel):
    """Only the fields present in the request change. The result must still satisfy the price rule."""

    name: str | None = Field(default=None, min_length=1, max_length=200)
    slug: str | None = Field(default=None, max_length=100, pattern=r"^[a-z0-9]+(-[a-z0-9]+)*$")
    admin_url: str | None = Field(default=None, max_length=2000)
    integration: Integration | None = None
    pricing_model: PricingModel | None = None
    price: PriceIn | None = None
    notes: str | None = None
    self_service: SelfServicePolicy | None = Field(
        default=None, description="Requests through the Slack agent: off, approval (an admin approves), automatic"
    )
    price_from_app: bool | None = Field(
        default=None,
        description="true: take the price from the app's billing again (400 without a billing read). "
        "A manual pricing_model or price change sets it to false",
    )


class AppListItem(ApiModel):
    id: uuid.UUID
    name: str
    slug: str
    admin_url: str | None
    integration: Integration
    pricing_model: PricingModel
    price: PriceOut | None = Field(description="In the app's own currency. Null for free apps")
    price_converted: PriceOut | None = Field(
        description="price in the organization currency; null for free apps and without a rate (show price)"
    )
    connector_key: str | None
    connection_status: ConnectionStatus | None = Field(description="Null when the app has no connection")
    last_synced_at: datetime | None
    active_seats: int = Field(description="Billable seats: active or invited accounts of kind person or unknown")
    accounts_count: int = Field(description="Accounts that are not removed")
    unassigned_count: int = Field(description="Not-removed accounts without a person that are not service accounts")
    monthly_cost: MoneyAmount | None = Field(description="In the app's own currency. Null for free apps")
    monthly_cost_converted: MoneyAmount | None = Field(
        description="monthly_cost in the organization currency; null without a rate (show monthly_cost)"
    )
    create_mode: WriteMode = Field(
        description=(
            "What 'Add to app' does: automatic (the connector creates the account after approval), "
            "writes_disabled (the connector can, but approval fails until 'Allow writes' is on), "
            "manual (a manual task)"
        )
    )
    delete_mode: WriteMode = Field(description="Same for removing an account (offboarding, 'Remove from app')")
    delete_suspends: bool = Field(description='The connector suspends instead of deleting; UI label "Suspend"')
    self_service: SelfServicePolicy = Field(description="What the Slack agent does when a person asks for an account")
    created_at: datetime


class AppPage(BaseModel):
    items: list[AppListItem]
    total: int


class AppBillingOut(ApiModel):
    """What the app's own billing reports, read by the sync."""

    plan: str | None
    pricing_model: PricingModel
    unit_amount: Money = Field(description="Per billed seat (per_seat) or for the whole plan (flat), per period")
    currency: str
    billing_period: BillingPeriod
    billed_seats: int | None = Field(description="Seats the app bills now, when it says")
    total_amount: Money | None = Field(description="What the app bills per period now, when it says")
    renews_on: date | None
    applies_to_price: bool = Field(description="The app's price follows this billing; false after a manual price")
    read_at: datetime


class AppDetail(AppListItem):
    notes: str | None
    connection: ConnectionOut | None
    billing: AppBillingOut | None = Field(description="Null when the connector does not read billing")
