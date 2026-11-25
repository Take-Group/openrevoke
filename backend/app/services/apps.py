"""Apps: list with seats and costs, detail, create, edit, delete."""

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING

from sqlalchemy import func, or_, select

from app.models import Account, Action, App, AppBilling, Connection
from app.models.enums import AccountStatus, ConnectionStatus, Integration, PricingModel
from app.schemas.actions import WriteKind
from app.schemas.apps import AppBillingOut, AppCreate, AppDetail, AppListItem, AppUpdate, PriceIn, PriceOut
from app.schemas.connections import ConnectionOut
from app.services import audit, billing, exchange_rates
from app.services.accounts import unassigned_clause
from app.services.capabilities import delete_suspends, write_mode
from app.services.costs import BILLABLE_KINDS, BILLABLE_STATUSES, Cost, app_monthly_cost
from app.services.errors import ConflictError, InvalidInputError, NotFoundError
from app.services.presenters import money, price_of
from app.services.secret_box import secret_names

if TYPE_CHECKING:
    import uuid

    from sqlalchemy.ext.asyncio import AsyncSession

    from app.services.conversion import Converter


@dataclass(frozen=True)
class SeatStats:
    accounts: int = 0
    billable: int = 0
    unassigned: int = 0


def slugify(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return slug[:90] or "app"


async def seat_stats(session: AsyncSession, app_ids: list[uuid.UUID] | None = None) -> dict[uuid.UUID, SeatStats]:
    """Per app: not-removed accounts, billable seats and unassigned accounts."""
    query = select(
        Account.app_id,
        func.count().filter(Account.status != AccountStatus.REMOVED),
        func.count().filter(Account.status.in_(BILLABLE_STATUSES), Account.kind.in_(BILLABLE_KINDS)),
        func.count().filter(unassigned_clause()),
    ).group_by(Account.app_id)
    if app_ids is not None:
        query = query.where(Account.app_id.in_(app_ids))
    rows = await session.execute(query)
    return {app_id: SeatStats(accounts, billable, unassigned) for app_id, accounts, billable, unassigned in rows}


async def list_apps(
    session: AsyncSession,
    *,
    q: str | None,
    status: ConnectionStatus | None,
    integration: Integration | None,
    limit: int,
    offset: int,
) -> tuple[list[AppListItem], int]:
    query = select(App, Connection).outerjoin(Connection, Connection.app_id == App.id)
    if q:
        pattern = f"%{q.strip()}%"
        query = query.where(or_(App.name.ilike(pattern), App.slug.ilike(pattern)))
    if status:
        query = query.where(Connection.status == status)
    if integration:
        query = query.where(App.integration == integration)
    total = await session.scalar(select(func.count()).select_from(query.subquery()))
    rows = list(await session.execute(query.order_by(func.lower(App.name), App.id).limit(limit).offset(offset)))
    stats = await seat_stats(session, [app.id for app, _ in rows])
    converter = await exchange_rates.load_converter(session)
    items = [_list_item(app, connection, stats.get(app.id, SeatStats()), converter) for app, connection in rows]
    return items, total or 0


async def get_app(session: AsyncSession, app_id: uuid.UUID) -> AppDetail:
    row = (
        await session.execute(
            select(App, Connection).outerjoin(Connection, Connection.app_id == App.id).where(App.id == app_id)
        )
    ).first()
    if row is None:
        raise NotFoundError("App not found")
    app, connection = row
    stats = (await seat_stats(session, [app.id])).get(app.id, SeatStats())
    item = _list_item(app, connection, stats, await exchange_rates.load_converter(session))
    billing_row = await session.get(AppBilling, app.id)
    return AppDetail(
        **item.model_dump(),
        notes=app.notes,
        connection=connection_out(connection) if connection else None,
        billing=AppBillingOut.model_validate(billing_row, from_attributes=True) if billing_row else None,
    )


async def create_app(session: AsyncSession, data: AppCreate) -> AppDetail:
    _check_price(data.pricing_model, data.price)
    slug = data.slug or await _free_slug(session, slugify(data.name))
    await _ensure_slug_free(session, slug, None)
    app = App(
        name=data.name.strip(),
        slug=slug,
        admin_url=_clean(data.admin_url),
        integration=data.integration,
        pricing_model=data.pricing_model,
        notes=data.notes,
        self_service=data.self_service,
    )
    _set_price(app, data.price)
    session.add(app)
    await session.flush()
    await audit.record(session, "app.created", "app", app.id, _snapshot(app))
    return await get_app(session, app.id)


async def update_app(session: AsyncSession, app_id: uuid.UUID, data: AppUpdate, fields: set[str]) -> AppDetail:
    app = await session.get(App, app_id)
    if app is None:
        raise NotFoundError("App not found")
    before = _snapshot(app)
    for name in ("name", "integration"):
        if name in fields:
            value = getattr(data, name)
            if value is None:
                raise InvalidInputError(f"{name} cannot be null")
            setattr(app, name, value.strip() if isinstance(value, str) else value)
    if "slug" in fields:
        if not data.slug:
            raise InvalidInputError("slug cannot be empty")
        await _ensure_slug_free(session, data.slug, app.id)
        app.slug = data.slug
    if "admin_url" in fields:
        app.admin_url = _clean(data.admin_url)
    if "notes" in fields:
        app.notes = data.notes
    if "self_service" in fields:
        if data.self_service is None:
            raise InvalidInputError("self_service cannot be null")
        app.self_service = data.self_service
    if "pricing_model" in fields or "price" in fields:
        pricing_model = data.pricing_model if "pricing_model" in fields and data.pricing_model else app.pricing_model
        if "price" in fields:
            price = data.price
        elif pricing_model == PricingModel.FREE:
            price = None
        else:
            price = _current_price(app)
        _check_price(pricing_model, price)
        old_price = (app.pricing_model, _current_price(app))
        app.pricing_model = pricing_model
        _set_price(app, price)
        if (app.pricing_model, _current_price(app)) != old_price:
            await billing.stop_applying(session, app.id)  # a person set another price: billing stops overwriting it
    if data.price_from_app:
        if "pricing_model" in fields or "price" in fields:
            raise InvalidInputError("Send either a price or price_from_app, not both")
        if not await billing.use_billing(session, app.id):
            raise InvalidInputError("The app has no billing read yet: sync its connection first")
    after = _snapshot(app)
    changes = {key: {"old": before[key], "new": after[key]} for key in after if before[key] != after[key]}
    if changes:
        await session.flush()
        await audit.record(session, "app.updated", "app", app.id, {"changes": changes})
    return await get_app(session, app.id)


async def delete_app(session: AsyncSession, app_id: uuid.UUID) -> uuid.UUID | None:
    """Delete an app without accounts and actions. Returns the id of its deleted connection, if any."""
    app = await session.get(App, app_id)
    if app is None:
        raise NotFoundError("App not found")
    if await session.scalar(select(func.count()).where(Account.app_id == app_id)):
        raise ConflictError("The app has accounts. Only an app without accounts can be deleted")
    if await session.scalar(select(func.count()).where(Action.app_id == app_id)):
        raise ConflictError("The app has actions in its history and cannot be deleted")
    snapshot = _snapshot(app)
    connection_id = await session.scalar(select(Connection.id).where(Connection.app_id == app_id))
    await session.delete(app)
    await session.flush()
    await audit.record(session, "app.deleted", "app", app_id, snapshot)
    return connection_id


def connection_out(connection: Connection) -> ConnectionOut:
    return ConnectionOut(
        id=connection.id,
        connector_key=connection.connector_key,
        config=connection.config or {},
        secrets_set=connection.secrets_encrypted is not None,
        secret_fields_set=secret_names(connection.secrets_encrypted),
        is_people_source=connection.is_people_source,
        writes_enabled=connection.writes_enabled,
        status=connection.status,
        last_synced_at=connection.last_synced_at,
        last_error=connection.last_error,
        created_at=connection.created_at,
    )


def _list_item(app: App, connection: Connection | None, stats: SeatStats, converter: Converter) -> AppListItem:
    cost = app_monthly_cost(price_of(app), stats.billable)
    return AppListItem(
        id=app.id,
        name=app.name,
        slug=app.slug,
        admin_url=app.admin_url,
        integration=app.integration,
        pricing_model=app.pricing_model,
        price=_current_price_out(app),
        price_converted=_converted_price_out(app, converter),
        connector_key=connection.connector_key if connection else None,
        connection_status=connection.status if connection else None,
        last_synced_at=connection.last_synced_at if connection else None,
        active_seats=stats.billable,
        accounts_count=stats.accounts,
        unassigned_count=stats.unassigned,
        monthly_cost=money(cost),
        monthly_cost_converted=money(converter.convert(cost)),
        create_mode=write_mode(connection, WriteKind.CREATE_ACCOUNT),
        delete_mode=write_mode(connection, WriteKind.DELETE_ACCOUNT),
        delete_suspends=delete_suspends(connection),
        self_service=app.self_service,
        created_at=app.created_at,
    )


def _check_price(pricing_model: PricingModel, price: PriceIn | None) -> None:
    if pricing_model == PricingModel.FREE and price is not None:
        raise InvalidInputError("A free app has no price. Set price to null or choose another pricing model")
    if pricing_model != PricingModel.FREE and price is None:
        raise InvalidInputError(f"Pricing model {pricing_model} needs a price")


def _set_price(app: App, price: PriceIn | None) -> None:
    app.price_amount = price.amount if price else None
    app.currency = price.currency.upper() if price else None
    if price:
        app.billing_period = price.billing_period


def _current_price(app: App) -> PriceIn | None:
    if app.price_amount is None or app.currency is None:
        return None
    return PriceIn(amount=app.price_amount, currency=app.currency, billing_period=app.billing_period)


def _current_price_out(app: App) -> PriceOut | None:
    if app.pricing_model == PricingModel.FREE or app.price_amount is None or app.currency is None:
        return None
    return PriceOut(amount=app.price_amount, currency=app.currency, billing_period=app.billing_period)


def _converted_price_out(app: App, converter: Converter) -> PriceOut | None:
    price = _current_price_out(app)
    if price is None:
        return None
    converted = converter.convert(Cost(price.currency, price.amount))
    if converted is None:
        return None
    return PriceOut(amount=converted.amount, currency=converted.currency, billing_period=price.billing_period)


async def _ensure_slug_free(session: AsyncSession, slug: str, app_id: uuid.UUID | None) -> None:
    owner = await session.scalar(select(App.id).where(App.slug == slug))
    if owner is not None and owner != app_id:
        raise ConflictError(f"Slug {slug} is already used by another app")


async def _free_slug(session: AsyncSession, base: str) -> str:
    taken = set(await session.scalars(select(App.slug).where(App.slug.like(f"{base}%"))))
    if base not in taken:
        return base
    suffix = 2
    while f"{base}-{suffix}" in taken:
        suffix += 1
    return f"{base}-{suffix}"


def _snapshot(app: App) -> dict[str, str | None]:
    return {
        "name": app.name,
        "slug": app.slug,
        "admin_url": app.admin_url,
        "integration": str(app.integration),
        "pricing_model": str(app.pricing_model),
        "price_amount": None if app.price_amount is None else str(app.price_amount),
        "currency": app.currency,
        "billing_period": str(app.billing_period),
        "notes": app.notes,
        "self_service": str(app.self_service),
    }


def _clean(value: str | None) -> str | None:
    return (value or "").strip() or None
