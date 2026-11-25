"""Currencies (public: the first-run setup needs them) and refreshing exchange rates (admin)."""

from fastapi import APIRouter

from app.api.auth_deps import AdminDep
from app.api.deps import SessionDep
from app.api.errors import UNAVAILABLE_RESPONSE
from app.schemas.currencies import CurrencyList, ExchangeRatesInfo
from app.services import exchange_rates
from app.services.currencies import KNOWN_CURRENCIES

public_router = APIRouter(prefix="/api", tags=["currencies"])
router = APIRouter(tags=["currencies"])


@public_router.get("/currencies", response_model=CurrencyList)
async def list_currencies(session: SessionDep) -> CurrencyList:
    _, rates = await exchange_rates.latest_rates(session)
    info = await exchange_rates.latest_info(session)
    return CurrencyList(
        codes=sorted(KNOWN_CURRENCIES),
        with_rates=sorted(code for code in rates if code in KNOWN_CURRENCIES),
        rates=ExchangeRatesInfo.model_validate(info) if info else None,
    )


@router.post("/exchange-rates/refresh", response_model=ExchangeRatesInfo, responses=UNAVAILABLE_RESPONSE)
async def refresh_exchange_rates(session: SessionDep, _: AdminDep) -> ExchangeRatesInfo:
    """Download today's rates now (they are also downloaded every day). 503 when no source answers."""
    return ExchangeRatesInfo.model_validate(await exchange_rates.refresh(session))
