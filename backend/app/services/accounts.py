"""Accounts in apps: listing, manual accounts, owner assignment and re-matching."""

import uuid
from collections.abc import Iterable
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import ColumnElement, and_, func, or_, select
from sqlalchemy.exc import IntegrityError

from app.models import Account, App, Person
from app.models.enums import AccountKind, AccountStatus, Integration, MatchMethod
from app.services import audit, exchange_rates
from app.services.errors import ConflictError, InvalidInputError, NotFoundError
from app.services.matching import load_email_index, match_email, normalize_email, resolve_match
from app.services.presenters import account_out

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from app.schemas.accounts import AccountCreate, AccountOut, AccountUpdate


def unassigned_clause() -> ColumnElement[bool]:
    """An account nobody owns: no person, not a service account, not removed."""
    return and_(
        Account.person_id.is_(None),
        Account.kind != AccountKind.SERVICE,
        Account.status != AccountStatus.REMOVED,
    )


def set_owner(account: Account, person_id: uuid.UUID | None, method: MatchMethod) -> bool:
    """Assign the owner. An owned account of unknown kind becomes a person account."""
    changed = account.person_id != person_id or account.match_method != method
    account.person_id = person_id
    account.match_method = method
    if person_id is not None and account.kind == AccountKind.UNKNOWN:
        account.kind = AccountKind.PERSON
    return changed


async def rematch_accounts(session: AsyncSession, emails: Iterable[str | None]) -> int:
    """Re-run e-mail matching for accounts with these e-mails. Manual assignments stay.

    Call it after a person's e-mail or aliases change, so accounts follow.
    Returns how many accounts changed owner.
    """
    normalized = {email for email in (normalize_email(value) for value in emails) if email}
    if not normalized:
        return 0
    accounts = await session.scalars(
        select(Account).where(Account.email.in_(normalized), Account.match_method != MatchMethod.MANUAL)
    )
    index = await load_email_index(session)
    changed = 0
    for account in accounts:
        previous = account.person_id
        result = resolve_match(index, account.email, account.person_id, account.match_method)
        if set_owner(account, result.person_id, result.method):
            changed += 1
            await audit.record(
                session,
                "account.matched" if result.person_id else "account.unmatched",
                "account",
                account.id,
                {"person_id": _str(result.person_id), "previous_person_id": _str(previous), "method": result.method},
            )
    await session.flush()
    return changed


async def list_app_accounts(
    session: AsyncSession,
    app_id: uuid.UUID,
    *,
    q: str | None,
    status: AccountStatus | None,
    kind: AccountKind | None,
    unassigned: bool,
    limit: int,
    offset: int,
) -> tuple[list[AccountOut], int]:
    app = await _get_app(session, app_id)
    query = select(Account, Person).outerjoin(Person, Person.id == Account.person_id).where(Account.app_id == app_id)
    if status:
        query = query.where(Account.status == status)
    if kind:
        query = query.where(Account.kind == kind)
    if unassigned:
        query = query.where(unassigned_clause())
    if q:
        pattern = f"%{q.strip()}%"
        query = query.where(
            or_(
                Account.email.ilike(pattern),
                Account.username.ilike(pattern),
                Account.display_name.ilike(pattern),
                Person.first_name.ilike(pattern),
                Person.last_name.ilike(pattern),
            )
        )
    total = await session.scalar(select(func.count()).select_from(query.subquery()))
    rows = await session.execute(
        query.order_by(Account.status, func.coalesce(Account.email, Account.username, Account.display_name), Account.id)
        .limit(limit)
        .offset(offset)
    )
    converter = await exchange_rates.load_converter(session)
    return [account_out(account, app, person, converter) for account, person in rows], total or 0


async def create_manual_account(session: AsyncSession, app_id: uuid.UUID, data: AccountCreate) -> AccountOut:
    app = await _get_app(session, app_id)
    if app.integration != Integration.MANUAL:
        raise ConflictError("Accounts can be added by hand only in apps with integration 'manual'")
    if data.status == AccountStatus.REMOVED:
        raise InvalidInputError("A new account cannot have status 'removed'")
    email = normalize_email(data.email)
    username = _clean(data.username)
    display_name = _clean(data.display_name)
    if not (email or username or display_name):
        raise InvalidInputError("Give at least one of email, username or display_name")

    now = datetime.now(UTC)
    account = Account(
        app_id=app.id,
        external_id=email or username or f"manual:{uuid.uuid4()}",
        email=email,
        username=username,
        display_name=display_name,
        role=_clean(data.role),
        status=data.status,
        kind=data.kind or AccountKind.UNKNOWN,
        last_seen_at=now,
    )
    if data.person_id is not None:
        await _get_person(session, data.person_id)
        set_owner(account, data.person_id, MatchMethod.MANUAL)
    else:
        result = await match_email(session, email)
        set_owner(account, result.person_id, result.method)
    session.add(account)
    try:
        await session.flush()
    except IntegrityError as exc:
        raise ConflictError("This app already has an account with this e-mail or username") from exc
    await audit.record(
        session,
        "account.created",
        "account",
        account.id,
        {"app_id": str(app.id), "email": email, "username": username, "person_id": _str(account.person_id)},
    )
    return await get_account_out(session, account.id)


async def update_account(
    session: AsyncSession, account_id: uuid.UUID, data: AccountUpdate, fields: set[str]
) -> AccountOut:
    account = await session.get(Account, account_id)
    if account is None:
        raise NotFoundError("Account not found")
    if {"role", "status", "display_name"} & fields and account.connection_id is not None:
        raise ConflictError("Role, status and display name of a synced account come from the app")
    changes: dict[str, dict[str, str | None]] = {}

    def note(field: str, old: object, new: object) -> None:
        if old != new:
            changes[field] = {"old": _str(old), "new": _str(new)}

    if "person_id" in fields:
        if data.person_id is not None:
            await _get_person(session, data.person_id)
        old_person, old_kind = account.person_id, account.kind
        set_owner(account, data.person_id, MatchMethod.MANUAL)
        note("person_id", old_person, account.person_id)
        note("kind", old_kind, account.kind)
    if "kind" in fields and data.kind is not None:
        note("kind", account.kind, data.kind)
        account.kind = data.kind

    if "role" in fields:
        note("role", account.role, _clean(data.role))
        account.role = _clean(data.role)
    if "display_name" in fields:
        note("display_name", account.display_name, _clean(data.display_name))
        account.display_name = _clean(data.display_name)
    if "status" in fields and data.status is not None and data.status != account.status:
        note("status", account.status, data.status)
        account.status = data.status
        account.removed_at = datetime.now(UTC) if data.status == AccountStatus.REMOVED else None

    if changes:
        await session.flush()
        await audit.record(session, "account.updated", "account", account.id, {"changes": changes})
    return await get_account_out(session, account.id)


async def get_account_out(session: AsyncSession, account_id: uuid.UUID) -> AccountOut:
    row = (
        await session.execute(
            select(Account, App, Person)
            .join(App, App.id == Account.app_id)
            .outerjoin(Person, Person.id == Account.person_id)
            .where(Account.id == account_id)
        )
    ).first()
    if row is None:
        raise NotFoundError("Account not found")
    account, app, person = row
    return account_out(account, app, person, await exchange_rates.load_converter(session))


async def _get_app(session: AsyncSession, app_id: uuid.UUID) -> App:
    app = await session.get(App, app_id)
    if app is None:
        raise NotFoundError("App not found")
    return app


async def _get_person(session: AsyncSession, person_id: uuid.UUID) -> Person:
    person = await session.get(Person, person_id)
    if person is None:
        raise InvalidInputError("Person not found")
    return person


def _clean(value: str | None) -> str | None:
    if value is None:
        return None
    return value.strip() or None


def _str(value: object) -> str | None:
    return None if value is None else str(value)
