import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import Boolean, Date, ForeignKey, Integer, String, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.columns import enum_column, money_column, timestamp
from app.models.enums import BillingPeriod, PricingModel


class AppBilling(Base):
    """The plan and price an app's own billing reports, read by the sync (one row per app).

    While ``applies_to_price`` is true, every read also sets the app's price fields, so all
    cost rules use what the app really charges. A manual price edit sets it to false.
    """

    __tablename__ = "app_billing"

    app_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("app.id", ondelete="CASCADE"), primary_key=True
    )
    plan: Mapped[str | None] = mapped_column(String(200))
    pricing_model: Mapped[PricingModel] = enum_column(PricingModel, "pricing_model", nullable=False)
    unit_amount: Mapped[Decimal | None] = money_column(nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    billing_period: Mapped[BillingPeriod] = enum_column(BillingPeriod, "billing_period", nullable=False)
    billed_seats: Mapped[int | None] = mapped_column(Integer)
    total_amount: Mapped[Decimal | None] = money_column()
    renews_on: Mapped[date | None] = mapped_column(Date)
    applies_to_price: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default=text("true"))
    raw: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict, server_default="{}")
    read_at: Mapped[datetime | None] = timestamp(nullable=False)
