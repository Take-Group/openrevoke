"""Converting costs to the organization currency.

Rates are stored per 1 EUR (``exchange_rate.per_eur``), whatever the source's
base, so any pair converts through EUR: ``amount / per_eur[from] * per_eur[to]``.
The original amount always stays in the response next to the converted one.
"""

from collections.abc import Iterable
from dataclasses import dataclass, field
from decimal import Decimal
from typing import TYPE_CHECKING

from app.services.costs import Cost

if TYPE_CHECKING:
    from datetime import date


@dataclass(frozen=True)
class Converter:
    target: str | None  # the organization currency; None before the first-run setup
    per_eur: dict[str, Decimal] = field(default_factory=dict)
    rates_date: date | None = None

    def can_convert(self, currency: str) -> bool:
        if self.target is None:
            return False
        return currency == self.target or (currency in self.per_eur and self.target in self.per_eur)

    def convert(self, cost: Cost | None) -> Cost | None:
        """The cost in the target currency. None without a rate (the caller shows the original)."""
        if cost is None or self.target is None or not self.can_convert(cost.currency):
            return None
        if cost.currency == self.target:
            return cost
        amount = cost.amount / self.per_eur[cost.currency] * self.per_eur[self.target]
        return Cost(self.target, amount)

    def total(self, costs: Iterable[Cost | None]) -> Cost | None:
        """Sum in the target currency. None when one of the costs has no rate: a partial sum would mislead."""
        if self.target is None:
            return None
        amount = Decimal(0)
        for cost in costs:
            if cost is None:
                continue
            converted = self.convert(cost)
            if converted is None:
                return None
            amount += converted.amount
        return Cost(self.target, amount)


NO_CONVERSION = Converter(target=None)
