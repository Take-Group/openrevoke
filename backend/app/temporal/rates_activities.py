"""Activity of ``RefreshExchangeRatesWorkflow``. It only calls ``app.services.exchange_rates``."""

from temporalio import activity

from app.database import async_session
from app.services import exchange_rates


@activity.defn
async def refresh_exchange_rates() -> str:
    async with async_session() as session, session.begin():
        info = await exchange_rates.refresh(session)
    return f"{info.source} {info.rates_date} ({info.currencies} currencies)"


RATES_ACTIVITIES = [refresh_exchange_rates]
