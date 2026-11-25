"""Build response schemas from models. Shared by the services that return them."""

from collections.abc import Iterable
from typing import TYPE_CHECKING

from app.schemas.accounts import AccountOut
from app.schemas.common import AccountRef, AppRef, MoneyAmount, PersonRef
from app.services.conversion import NO_CONVERSION, Converter
from app.services.costs import Cost, Price, seat_monthly_cost

if TYPE_CHECKING:
    from app.models import Account, App, Person


def price_of(app: App) -> Price:
    return Price(app.pricing_model, app.price_amount, app.currency, app.billing_period)


def money(cost: Cost | None) -> MoneyAmount | None:
    return None if cost is None else MoneyAmount(currency=cost.currency, amount=cost.amount)


def money_list(costs: Iterable[Cost]) -> list[MoneyAmount]:
    return [MoneyAmount(currency=cost.currency, amount=cost.amount) for cost in costs]


def app_ref(app: App) -> AppRef:
    return AppRef(app_id=app.id, name=app.name, slug=app.slug)


def person_ref(person: Person | None) -> PersonRef | None:
    if person is None:
        return None
    return PersonRef(
        person_id=person.id,
        first_name=person.first_name,
        last_name=person.last_name,
        primary_email=person.primary_email,
        status=person.status,
    )


def account_cost(account: Account, app: App) -> Cost | None:
    return seat_monthly_cost(price_of(app), account.status, account.kind)


def account_out(account: Account, app: App, person: Person | None, converter: Converter = NO_CONVERSION) -> AccountOut:
    cost = account_cost(account, app)
    return AccountOut(
        id=account.id,
        app_id=account.app_id,
        connection_id=account.connection_id,
        external_id=account.external_id,
        email=account.email,
        username=account.username,
        display_name=account.display_name,
        role=account.role,
        status=account.status,
        kind=account.kind,
        match_method=account.match_method,
        person=person_ref(person),
        monthly_cost=money(cost),
        monthly_cost_converted=money(converter.convert(cost)),
        first_seen_at=account.first_seen_at,
        last_seen_at=account.last_seen_at,
        removed_at=account.removed_at,
    )


def account_ref(account: Account | None) -> AccountRef | None:
    if account is None:
        return None
    return AccountRef(
        account_id=account.id,
        email=account.email,
        username=account.username,
        display_name=account.display_name,
        status=account.status,
    )
