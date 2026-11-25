"""Prices read from an app's own billing (``Capability.READ_BILLING``), stored by the sync.

``apply_billing`` keeps one ``app_billing`` row per app. While its
``applies_to_price`` is true, the app's price fields follow the billing, so
every cost rule (``services/costs.py``) uses what the app really charges. A
manual price edit turns that off (``stop_applying``); ``use_billing`` turns
it back on.
"""

from datetime import UTC, datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from app.models import App, AppBilling
from app.models.enums import BillingPeriod, PricingModel
from app.services import audit

if TYPE_CHECKING:
    import uuid

    from sqlalchemy.ext.asyncio import AsyncSession

    from app.connectors.base import BillingInfo


async def apply_billing(session: AsyncSession, app_id: uuid.UUID, info: BillingInfo) -> None:
    row = await session.get(AppBilling, app_id)
    if row is None:
        row = AppBilling(app_id=app_id, applies_to_price=True)
        session.add(row)
    row.plan = info.plan
    row.pricing_model = PricingModel(info.pricing_model)
    row.unit_amount = info.unit_amount
    row.currency = info.currency.upper()
    row.billing_period = BillingPeriod(info.billing_period)
    row.billed_seats = info.billed_seats
    row.total_amount = info.total_amount
    row.renews_on = info.renews_on
    row.raw = dict(info.raw)
    row.read_at = datetime.now(UTC)
    if row.applies_to_price:
        await _set_app_price(session, app_id, row)


async def stop_applying(session: AsyncSession, app_id: uuid.UUID) -> None:
    """A person set the price by hand: the billing no longer overwrites it."""
    row = await session.get(AppBilling, app_id)
    if row is not None:
        row.applies_to_price = False


async def use_billing(session: AsyncSession, app_id: uuid.UUID) -> bool:
    """Take the price from the last billing read again. False when the app has none."""
    row = await session.get(AppBilling, app_id)
    if row is None:
        return False
    row.applies_to_price = True
    await _set_app_price(session, app_id, row)
    return True


async def _set_app_price(session: AsyncSession, app_id: uuid.UUID, row: AppBilling) -> None:
    app = await session.get(App, app_id)
    if app is None:
        return
    before = _price(app)
    if row.pricing_model == PricingModel.FLAT and row.unit_amount == Decimal(0):
        app.pricing_model, app.price_amount, app.currency = PricingModel.FREE, None, None
    else:
        app.pricing_model = row.pricing_model
        app.price_amount = row.unit_amount
        app.currency = row.currency
        app.billing_period = row.billing_period
    after = _price(app)
    if before != after:
        await session.flush()
        await audit.record(session, "app.price_from_billing", "app", app_id, {"old": before, "new": after})


def _price(app: App) -> dict[str, Any]:
    return {
        "pricing_model": str(app.pricing_model),
        "amount": str(app.price_amount) if app.price_amount is not None else None,
        "currency": app.currency,
        "billing_period": str(app.billing_period),
    }
