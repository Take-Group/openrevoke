from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class ExchangeRate(Base):
    """Daily exchange rates, one row per day and currency, as units of the currency per 1 EUR."""

    __tablename__ = "exchange_rate"

    rate_date: Mapped[date] = mapped_column(Date, primary_key=True)
    currency: Mapped[str] = mapped_column(String(3), primary_key=True)
    per_eur: Mapped[Decimal] = mapped_column(Numeric(28, 12, asdecimal=True), nullable=False)
    source: Mapped[str] = mapped_column(String(50), nullable=False)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
