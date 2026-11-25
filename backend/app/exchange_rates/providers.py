"""Sources of exchange rates. ``RateProvider`` is the abstraction; the first that answers wins.

1. ExchangeRate-API "Open Access" (https://www.exchangerate-api.com/docs/free): no key,
   166 currencies, updated once a day. Terms ask for attribution ("Rates by
   Exchange Rate API" with a link) and at most one request an hour.
2. fawazahmed0/exchange-api on jsDelivr (https://github.com/fawazahmed0/exchange-api):
   no key, CC0, daily. Also lists crypto and metals; only ISO codes are kept.
"""

from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any, Protocol

import httpx

from app.services.currencies import CODE, KNOWN_CURRENCIES

TIMEOUT_SECONDS = 20


class RatesUnavailableError(Exception):
    """The source did not answer or answered something unusable."""


@dataclass(frozen=True)
class RateSnapshot:
    source: str
    rate_date: date
    per_eur: dict[str, Decimal]  # units of the currency for 1 EUR; EUR itself is 1


class RateProvider(Protocol):
    name: str
    attribution_url: str

    async def fetch(self, http: httpx.AsyncClient) -> RateSnapshot: ...


def _decimal(value: Any) -> Decimal | None:
    try:
        number = Decimal(str(value))
    except InvalidOperation, ValueError:
        return None
    return number if number.is_finite() and number > 0 else None


def _iso_rates(raw: dict[str, Any]) -> dict[str, Decimal]:
    rates: dict[str, Decimal] = {}
    for code, value in raw.items():
        code = str(code).upper()
        number = _decimal(value)
        if CODE.match(code) and code in KNOWN_CURRENCIES and number is not None:
            rates[code] = number
    return rates


def _to_eur_base(rates: dict[str, Decimal], base: str) -> dict[str, Decimal]:
    """Rates per 1 ``base`` → rates per 1 EUR."""
    eur = rates.get("EUR")
    if eur is None:
        raise RatesUnavailableError("The answer has no EUR rate")
    per_eur = {code: value / eur for code, value in rates.items()}
    per_eur["EUR"] = Decimal(1)
    per_eur.setdefault(base, 1 / eur)
    return per_eur


async def _get_json(http: httpx.AsyncClient, url: str) -> dict[str, Any]:
    try:
        response = await http.get(url, timeout=TIMEOUT_SECONDS)
        response.raise_for_status()
        data = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise RatesUnavailableError(f"{url}: {exc}") from exc
    if not isinstance(data, dict):
        raise RatesUnavailableError(f"{url}: not a JSON object")
    return data


def parse_open_er_api(data: dict[str, Any]) -> RateSnapshot:
    if data.get("result") != "success" or not isinstance(data.get("rates"), dict):
        raise RatesUnavailableError(f"ExchangeRate-API: {data.get('error-type') or 'unexpected answer'}")
    base = str(data.get("base_code", "")).upper()
    updated = data.get("time_last_update_unix")
    rate_date = datetime.fromtimestamp(int(updated), UTC).date() if updated else datetime.now(UTC).date()
    return RateSnapshot("exchangerate-api", rate_date, _to_eur_base(_iso_rates(data["rates"]), base))


def parse_currency_api(data: dict[str, Any]) -> RateSnapshot:
    raw = data.get("eur")
    if not isinstance(raw, dict):
        raise RatesUnavailableError("currency-api: no 'eur' object")
    try:
        rate_date = date.fromisoformat(str(data.get("date")))
    except ValueError as exc:
        raise RatesUnavailableError("currency-api: no date") from exc
    rates = _iso_rates(raw)
    rates["EUR"] = Decimal(1)
    return RateSnapshot("currency-api", rate_date, rates)


class OpenErApiProvider:
    name = "ExchangeRate-API"
    attribution_url = "https://www.exchangerate-api.com"
    url = "https://open.er-api.com/v6/latest/EUR"

    async def fetch(self, http: httpx.AsyncClient) -> RateSnapshot:
        return parse_open_er_api(await _get_json(http, self.url))


class CurrencyApiProvider:
    name = "fawazahmed0/exchange-api"
    attribution_url = "https://github.com/fawazahmed0/exchange-api"
    urls = (
        "https://cdn.jsdelivr.net/npm/@fawazahmed0/currency-api@latest/v1/currencies/eur.json",
        "https://latest.currency-api.pages.dev/v1/currencies/eur.json",
    )

    async def fetch(self, http: httpx.AsyncClient) -> RateSnapshot:
        errors: list[str] = []
        for url in self.urls:
            try:
                return parse_currency_api(await _get_json(http, url))
            except RatesUnavailableError as exc:
                errors.append(str(exc))
        raise RatesUnavailableError("; ".join(errors))


DEFAULT_PROVIDERS: tuple[RateProvider, ...] = (OpenErApiProvider(), CurrencyApiProvider())
SOURCE_NAMES = {"exchangerate-api": OpenErApiProvider, "currency-api": CurrencyApiProvider}
