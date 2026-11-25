"""Monthly cost rules.

- per_seat: price x billable seats. A seat is an account with status
  active or invited and kind person or unknown (service accounts excluded).
  A person's cost is the sum of the seat prices of their accounts.
- flat: the whole amount belongs to the app, never to people.
- free: no cost.
- yearly prices are divided by 12.
- Currencies are summed separately here; ``app.services.conversion`` converts
  them to the organization currency with the daily rates.

Values keep full precision; rounding to cents happens only on output.
"""

from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass
from decimal import Decimal

from app.models.enums import AccountKind, AccountStatus, BillingPeriod, PricingModel

BILLABLE_STATUSES = frozenset({AccountStatus.ACTIVE, AccountStatus.INVITED})
BILLABLE_KINDS = frozenset({AccountKind.PERSON, AccountKind.UNKNOWN})
MONTHS_PER_YEAR = Decimal(12)


@dataclass(frozen=True)
class Price:
    pricing_model: PricingModel
    amount: Decimal | None
    currency: str | None
    billing_period: BillingPeriod


@dataclass(frozen=True)
class Cost:
    currency: str
    amount: Decimal


def is_billable_seat(status: AccountStatus, kind: AccountKind) -> bool:
    return status in BILLABLE_STATUSES and kind in BILLABLE_KINDS


def monthly_price(price: Price) -> Cost | None:
    """The price per month: of one seat (per_seat) or of the whole app (flat)."""
    if price.pricing_model == PricingModel.FREE or price.amount is None or price.currency is None:
        return None
    amount = price.amount
    if price.billing_period == BillingPeriod.YEARLY:
        amount = amount / MONTHS_PER_YEAR
    return Cost(price.currency, amount)


def app_monthly_cost(price: Price, billable_seats: int) -> Cost | None:
    base = monthly_price(price)
    if base is None:
        return None
    if price.pricing_model == PricingModel.PER_SEAT:
        return Cost(base.currency, base.amount * billable_seats)
    return base


def seat_monthly_cost(price: Price, status: AccountStatus, kind: AccountKind) -> Cost | None:
    """What one account adds to its owner's cost. Only per_seat apps charge people."""
    if price.pricing_model != PricingModel.PER_SEAT or not is_billable_seat(status, kind):
        return None
    return monthly_price(price)


def sum_by_currency(costs: Iterable[Cost | None]) -> list[Cost]:
    totals: dict[str, Decimal] = defaultdict(Decimal)
    for cost in costs:
        if cost is not None:
            totals[cost.currency] += cost.amount
    return [Cost(currency, totals[currency]) for currency in sorted(totals)]
