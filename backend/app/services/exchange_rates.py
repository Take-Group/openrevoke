"""Store and read daily exchange rates; build the ``Converter`` for a request.

``refresh`` runs once a day (``RefreshExchangeRatesWorkflow``, Temporal Schedule)
and from "Refresh rates" in the panel. A failed download keeps the last rates.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal
from typing import TYPE_CHECKING

import httpx
import structlog
from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert

from app.connectors.http import USER_AGENT
from app.exchange_rates.providers import DEFAULT_PROVIDERS, RateProvider, RateSnapshot, RatesUnavailableError
from app.models import ExchangeRate, Organization
from app.services.conversion import Converter
from app.services.errors import UnavailableError

if TYPE_CHECKING:
    from datetime import date, datetime

    from sqlalchemy.ext.asyncio import AsyncSession

logger = structlog.get_logger()

ATTRIBUTION = {
    provider_key: url
    for provider_key, url in (
        ("exchangerate-api", "https://www.exchangerate-api.com"),
        ("currency-api", "https://github.com/fawazahmed0/exchange-api"),
    )
}


@dataclass(frozen=True)
class RatesInfo:
    rates_date: date
    source: str
    source_url: str | None
    fetched_at: datetime
    currencies: int


async def fetch_snapshot(providers: Sequence[RateProvider] = DEFAULT_PROVIDERS) -> RateSnapshot:
    """Rates from the first source that answers."""
    errors: list[str] = []
    async with httpx.AsyncClient(headers={"User-Agent": USER_AGENT}, follow_redirects=True) as http:
        for provider in providers:
            try:
                snapshot = await provider.fetch(http)
            except RatesUnavailableError as exc:
                logger.warning("exchange_rates_source_failed", source=provider.name, error=str(exc))
                errors.append(f"{provider.name}: {exc}")
                continue
            if len(snapshot.per_eur) < 2:
                errors.append(f"{provider.name}: no rates")
                continue
            return snapshot
    raise UnavailableError("No exchange rate source answered. " + " | ".join(errors))


async def store(session: AsyncSession, snapshot: RateSnapshot) -> int:
    rows = [
        {"rate_date": snapshot.rate_date, "currency": code, "per_eur": rate, "source": snapshot.source}
        for code, rate in sorted(snapshot.per_eur.items())
    ]
    statement = insert(ExchangeRate).values(rows)
    statement = statement.on_conflict_do_update(
        index_elements=[ExchangeRate.rate_date, ExchangeRate.currency],
        set_={"per_eur": statement.excluded.per_eur, "source": statement.excluded.source, "fetched_at": func.now()},
    )
    await session.execute(statement)
    return len(rows)


async def refresh(session: AsyncSession, providers: Sequence[RateProvider] = DEFAULT_PROVIDERS) -> RatesInfo:
    snapshot = await fetch_snapshot(providers)
    count = await store(session, snapshot)
    await session.flush()
    logger.info("exchange_rates_refreshed", source=snapshot.source, date=str(snapshot.rate_date), currencies=count)
    info = await latest_info(session)
    assert info is not None
    return info


async def _latest_date(session: AsyncSession) -> date | None:
    return await session.scalar(select(func.max(ExchangeRate.rate_date)))


async def latest_info(session: AsyncSession) -> RatesInfo | None:
    rate_date = await _latest_date(session)
    if rate_date is None:
        return None
    source, fetched_at, count = (
        await session.execute(
            select(func.min(ExchangeRate.source), func.max(ExchangeRate.fetched_at), func.count()).where(
                ExchangeRate.rate_date == rate_date
            )
        )
    ).one()
    return RatesInfo(rate_date, source, ATTRIBUTION.get(source), fetched_at, count)


async def latest_rates(session: AsyncSession) -> tuple[date | None, dict[str, Decimal]]:
    rate_date = await _latest_date(session)
    if rate_date is None:
        return None, {}
    rows = await session.execute(
        select(ExchangeRate.currency, ExchangeRate.per_eur).where(ExchangeRate.rate_date == rate_date)
    )
    return rate_date, {code: Decimal(rate) for code, rate in rows}


async def load_converter(session: AsyncSession) -> Converter:
    """Organization currency and the newest rates. One call per request that shows costs."""
    organization = await session.get(Organization, 1)
    rate_date, per_eur = await latest_rates(session)
    return Converter(target=organization.currency if organization else None, per_eur=per_eur, rates_date=rate_date)


async def has_rates_for(session: AsyncSession, day: date) -> bool:
    latest = await _latest_date(session)
    return latest is not None and latest >= day
