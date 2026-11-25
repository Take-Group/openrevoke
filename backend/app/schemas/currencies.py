"""Currencies and the exchange rates the panel converts costs with."""

from datetime import date, datetime

from pydantic import BaseModel, Field

from app.schemas.common import ApiModel


class ExchangeRatesInfo(ApiModel):
    rates_date: date = Field(description="Day of the newest stored rates")
    source: str = Field(description="exchangerate-api or currency-api")
    source_url: str | None = Field(description="Link for attribution")
    fetched_at: datetime
    currencies: int


class CurrencyList(BaseModel):
    codes: list[str] = Field(description="ISO 4217 codes the organization currency can be")
    with_rates: list[str] = Field(description="Codes with a stored rate (their amounts convert)")
    rates: ExchangeRatesInfo | None = Field(description="Null before the first download")
