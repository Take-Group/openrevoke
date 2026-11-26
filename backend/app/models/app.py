import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, LargeBinary, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.columns import created_at_column, enum_column, money_column, uuid_pk
from app.models.enums import BillingPeriod, Integration, PricingModel, RequestPolicy


class App(Base):
    """A SaaS application the company pays for or uses."""

    __tablename__ = "app"
    __table_args__ = (
        CheckConstraint(
            "pricing_model = 'free' OR (price_amount IS NOT NULL AND currency IS NOT NULL)",
            name="price_required",
        ),
        CheckConstraint("price_amount IS NULL OR price_amount >= 0", name="price_non_negative"),
        CheckConstraint("currency IS NULL OR currency ~ '^[A-Z]{3}$'", name="currency_iso"),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    admin_url: Mapped[str | None] = mapped_column(String(2000))
    integration: Mapped[Integration] = enum_column(
        Integration, "integration", nullable=False, default=Integration.MANUAL
    )
    pricing_model: Mapped[PricingModel] = enum_column(
        PricingModel, "pricing_model", nullable=False, default=PricingModel.FREE
    )
    price_amount: Mapped[Decimal | None] = money_column()
    currency: Mapped[str | None] = mapped_column(String(3))
    billing_period: Mapped[BillingPeriod] = enum_column(
        BillingPeriod, "billing_period", nullable=False, default=BillingPeriod.MONTHLY
    )
    notes: Mapped[str | None] = mapped_column(Text)
    # Who approves when a person asks for an account here (panel, Slack agent, API).
    request_policy: Mapped[RequestPolicy] = enum_column(
        RequestPolicy, "request_policy", nullable=False, default=RequestPolicy.MANAGER
    )
    # Slug in the bundled catalog (app/catalog/apps.json): logo and website when none is set here.
    catalog_key: Mapped[str | None] = mapped_column(String(100), index=True)
    website: Mapped[str | None] = mapped_column(String(500))
    category: Mapped[str | None] = mapped_column(String(50))
    # Logo uploaded by an admin (PNG, JPEG, WebP or SVG, at most 256 KB); wins over the catalog's.
    logo: Mapped[bytes | None] = mapped_column(LargeBinary, deferred=True)
    logo_content_type: Mapped[str | None] = mapped_column(String(50))
    created_at: Mapped[datetime] = created_at_column()
