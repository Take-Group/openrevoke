"""People: list with costs, detail, manual create, edit (status, aliases, manager) and delete."""

from collections import defaultdict
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import exists, func, or_, select

from app.models import Account, Action, App, Person, PersonEmail, PersonLink
from app.models.enums import (
    AccountStatus,
    PeopleSourceKind,
    PersonKind,
    PersonKindSource,
    PersonLinkSource,
    PersonStatus,
)
from app.schemas.people import (
    AliasOut,
    PersonAccountOut,
    PersonCreate,
    PersonDetail,
    PersonListItem,
    PersonSourceOut,
    PersonUpdate,
)
from app.services import audit, exchange_rates, people_managers
from app.services.access.managers import manager_of
from app.services.accounts import rematch_accounts
from app.services.costs import sum_by_currency
from app.services.errors import ConflictError, InvalidInputError, NotFoundError
from app.services.matching import email_owner, is_valid_email, normalize_email
from app.services.people_sources import get_or_create_source, source_names, upsert_link
from app.services.presenters import account_cost, account_out, app_ref, money, money_list, person_ref

if TYPE_CHECKING:
    import uuid

    from sqlalchemy.ext.asyncio import AsyncSession

    from app.services.conversion import Converter


def clean_email(value: str, field: str = "email") -> str:
    email = normalize_email(value)
    if email is None or not is_valid_email(email):
        raise InvalidInputError(f"Invalid {field}: {value!r}")
    return email


def clean_code(value: str | None) -> str | None:
    return (value or "").strip() or None


def clean_text(value: str | None) -> str | None:
    """Department, job title: trimmed, empty means none."""
    return (value or "").strip()[:200] or None


async def ensure_email_free(session: AsyncSession, email: str, person_id: uuid.UUID | None) -> None:
    """An e-mail (primary or alias) may belong to one person only."""
    owner = await email_owner(session, email)
    if owner is not None and owner != person_id:
        raise ConflictError(f"E-mail {email} already belongs to another person")


async def ensure_code_free(session: AsyncSession, code: str | None, person_id: uuid.UUID | None) -> None:
    if code is None:
        return
    owner = await session.scalar(select(Person.id).where(Person.employee_code == code))
    if owner is not None and owner != person_id:
        raise ConflictError(f"Employee code {code} already belongs to another person")


async def clean_aliases(
    session: AsyncSession, aliases: list[str], primary_email: str, person_id: uuid.UUID | None
) -> list[str]:
    result: list[str] = []
    for value in aliases:
        alias = clean_email(value, "alias")
        if alias == primary_email or alias in result:
            continue
        await ensure_email_free(session, alias, person_id)
        result.append(alias)
    return result


async def list_people(
    session: AsyncSession,
    *,
    q: str | None,
    status: PersonStatus | None,
    kind: PersonKind | None,
    limit: int,
    offset: int,
    no_manager: bool = False,
) -> tuple[list[PersonListItem], int, dict[PersonKind, int]]:
    query = select(Person)
    if status:
        query = query.where(Person.status == status)
    if no_manager:
        query = query.where(people_managers.without_manager_clause())
    if q:
        pattern = f"%{q.strip()}%"
        query = query.where(
            or_(
                (Person.first_name + " " + Person.last_name).ilike(pattern),
                Person.primary_email.ilike(pattern),
                Person.employee_code.ilike(pattern),
                Person.department.ilike(pattern),
                Person.job_title.ilike(pattern),
                exists().where(PersonEmail.person_id == Person.id, PersonEmail.email.ilike(pattern)),
            )
        )
    by_kind = query.subquery()
    kind_counts = {kind: 0 for kind in PersonKind} | dict(
        (await session.execute(select(by_kind.c.kind, func.count()).group_by(by_kind.c.kind))).all()
    )
    if kind:
        query = query.where(Person.kind == kind)
    total = await session.scalar(select(func.count()).select_from(query.subquery()))
    people = list(
        await session.scalars(
            query.order_by(Person.last_name, Person.first_name, Person.id).limit(limit).offset(offset)
        )
    )
    accounts = await _live_accounts(session, [person.id for person in people])
    managers = await people_managers.people_by_id(session, {p.manager_id for p in people if p.manager_id})
    converter = await exchange_rates.load_converter(session)
    items = [
        _list_item(person, accounts.get(person.id, []), converter, managers.get(person.manager_id)) for person in people
    ]
    return items, total or 0, kind_counts


async def get_person(session: AsyncSession, person_id: uuid.UUID) -> PersonDetail:
    person = await session.get(Person, person_id)
    if person is None:
        raise NotFoundError("Person not found")
    aliases = list(
        await session.scalars(select(PersonEmail).where(PersonEmail.person_id == person_id).order_by(PersonEmail.email))
    )
    links = list(await session.scalars(select(PersonLink).where(PersonLink.person_id == person_id)))
    names = await source_names(session, links)
    rows = await session.execute(
        select(Account, App)
        .join(App, App.id == Account.app_id)
        .where(Account.person_id == person_id)
        .order_by(Account.status == AccountStatus.REMOVED, App.name)
    )
    all_accounts = list(rows)
    has_actions = bool(await session.scalar(select(exists().where(Action.person_id == person_id))))
    live = [(account, app) for account, app in all_accounts if account.status != AccountStatus.REMOVED]
    converter = await exchange_rates.load_converter(session)
    manager = await manager_of(session, person)
    item = _list_item(person, live, converter, manager)
    reports = await people_managers.reports_of(session, person_id)
    return PersonDetail(
        **item.model_dump(),
        notes=person.notes,
        aliases=[AliasOut.model_validate(alias) for alias in aliases],
        sources=[
            PersonSourceOut(
                id=link.id,
                source_type=link.source_type,
                source_id=link.source_id,
                source_name=names.get(link.source_id, "Unknown source"),
                external_id=link.external_id,
                is_active=link.is_active,
                last_seen_at=link.last_seen_at,
            )
            for link in links
        ],
        accounts=[
            PersonAccountOut(**account_out(account, app, person, converter).model_dump(), app=app_ref(app))
            for account, app in all_accounts
        ],
        can_delete=not all_accounts and not has_actions,
        reports=[ref for ref in map(person_ref, reports) if ref is not None],
    )


async def delete_person(session: AsyncSession, person_id: uuid.UUID) -> None:
    """Delete a person entered by mistake. Only without accounts and actions (409), so no history is lost."""
    person = await session.get(Person, person_id)
    if person is None:
        raise NotFoundError("Person not found")
    if await session.scalar(select(exists().where(Account.person_id == person_id))):
        raise ConflictError("The person has accounts. Only a person without accounts and actions can be deleted")
    if await session.scalar(select(exists().where(Action.person_id == person_id))):
        raise ConflictError("The person has actions in the history and cannot be deleted. Use offboarding instead")
    snapshot = {
        "primary_email": person.primary_email,
        "first_name": person.first_name,
        "last_name": person.last_name,
        "employee_code": person.employee_code,
    }
    await session.delete(person)  # aliases and source links go with it (ON DELETE CASCADE)
    await session.flush()
    await audit.record(session, "person.deleted", "person", person_id, snapshot)


async def create_person(session: AsyncSession, data: PersonCreate) -> PersonDetail:
    email = clean_email(data.primary_email, "primary_email")
    await ensure_email_free(session, email, None)
    code = clean_code(data.employee_code)
    await ensure_code_free(session, code, None)
    aliases = await clean_aliases(session, data.aliases, email, None)

    person = Person(
        first_name=data.first_name.strip(),
        last_name=data.last_name.strip(),
        primary_email=email,
        employee_code=code,
        notes=data.notes,
        department=clean_text(data.department),
        job_title=clean_text(data.job_title),
        status=PersonStatus.ACTIVE,
        kind_source=PersonKindSource.MANUAL,  # typed in by an admin: a person, whatever the rules say
    )
    session.add(person)
    await session.flush()
    if data.manager_id is not None:
        await people_managers.set_manager(session, person, data.manager_id)
    session.add_all(PersonEmail(person_id=person.id, email=alias) for alias in aliases)
    source = await get_or_create_source(session, PeopleSourceKind.MANUAL)
    await upsert_link(
        session, person_id=person.id, source_type=PersonLinkSource.MANUAL, source_id=source.id, external_id=email
    )
    await audit.record(
        session, "person.created", "person", person.id, {"primary_email": email, "aliases": aliases, "via": "manual"}
    )
    await rematch_accounts(session, [email, *aliases])
    return await get_person(session, person.id)


async def update_person(
    session: AsyncSession, person_id: uuid.UUID, data: PersonUpdate, fields: set[str]
) -> PersonDetail:
    person = await session.get(Person, person_id)
    if person is None:
        raise NotFoundError("Person not found")
    changes: dict[str, dict[str, str | None]] = {}
    touched_emails: set[str] = set()

    def note(field: str, old: object, new: object) -> None:
        if old != new:
            changes[field] = {"old": None if old is None else str(old), "new": None if new is None else str(new)}

    for field in ("first_name", "last_name"):
        if field in fields:
            value = getattr(data, field)
            if value is None:
                raise InvalidInputError(f"{field} cannot be empty")
            note(field, getattr(person, field), value.strip())
            setattr(person, field, value.strip())
    if "notes" in fields:
        note("notes", person.notes, data.notes)
        person.notes = data.notes
    for field in ("department", "job_title"):
        if field in fields:
            value = clean_text(getattr(data, field))
            note(field, getattr(person, field), value)
            setattr(person, field, value)
    if "manager_id" in fields:
        old_manager, old_source = person.manager_id, person.manager_source
        await people_managers.set_manager(session, person, data.manager_id)
        note("manager_id", old_manager, person.manager_id)
        note("manager_source", old_source, person.manager_source)
    if "kind" in fields:
        if data.kind is None:
            raise InvalidInputError("kind cannot be empty")
        note("kind", person.kind, data.kind)
        person.kind = data.kind
        person.kind_source = PersonKindSource.MANUAL  # syncs keep the admin's choice
        person.kind_reason = None
    if "employee_code" in fields:
        code = clean_code(data.employee_code)
        await ensure_code_free(session, code, person.id)
        note("employee_code", person.employee_code, code)
        person.employee_code = code
    if "primary_email" in fields:
        if data.primary_email is None:
            raise InvalidInputError("primary_email cannot be empty")
        email = clean_email(data.primary_email, "primary_email")
        if email != person.primary_email:
            await ensure_email_free(session, email, person.id)
            # The new primary e-mail may have been an alias of the same person.
            await _delete_aliases(session, person.id, {email})
            touched_emails |= {person.primary_email, email}
            note("primary_email", person.primary_email, email)
            person.primary_email = email
    if "aliases" in fields and data.aliases is not None:
        await _replace_aliases(session, person, data.aliases, note, touched_emails)
    if "status" in fields or "left_at" in fields:
        _apply_status(person, data, fields, note)

    if changes:
        await session.flush()
        await audit.record(session, "person.updated", "person", person.id, {"changes": changes})
        await rematch_accounts(session, touched_emails)
        if {"manager_id", "status", "primary_email", "aliases"} & changes.keys():
            from app.services.access.flow import reroute_pending  # late: flow imports the action services

            await reroute_pending(session)  # requests waiting for a manager follow the change
    return await get_person(session, person.id)


def _apply_status(person: Person, data: PersonUpdate, fields: set[str], note) -> None:
    status = data.status if "status" in fields and data.status is not None else person.status
    if status == PersonStatus.LEFT:
        left_at = data.left_at if "left_at" in fields and data.left_at else (person.left_at or datetime.now(UTC))
    else:
        if "left_at" in fields and data.left_at is not None:
            raise InvalidInputError("left_at can be set only together with status 'left'")
        left_at = None
    note("status", person.status, status)
    note("left_at", person.left_at, left_at)
    person.status = status
    person.left_at = left_at


async def _replace_aliases(session: AsyncSession, person: Person, values: list[str], note, touched: set[str]) -> None:
    current = {
        alias.email: alias
        for alias in await session.scalars(select(PersonEmail).where(PersonEmail.person_id == person.id))
    }
    wanted = await clean_aliases(session, values, person.primary_email, person.id)
    removed = set(current) - set(wanted)
    added = [alias for alias in wanted if alias not in current]
    if not removed and not added:
        return
    await _delete_aliases(session, person.id, removed)
    session.add_all(PersonEmail(person_id=person.id, email=alias) for alias in added)
    await session.flush()
    note("aliases", ", ".join(sorted(current)), ", ".join(sorted(wanted)))
    touched |= removed | set(added)


async def _delete_aliases(session: AsyncSession, person_id: uuid.UUID, emails: set[str]) -> None:
    if not emails:
        return
    for alias in await session.scalars(
        select(PersonEmail).where(PersonEmail.person_id == person_id, PersonEmail.email.in_(emails))
    ):
        await session.delete(alias)
    await session.flush()


async def _live_accounts(
    session: AsyncSession, person_ids: list[uuid.UUID]
) -> dict[uuid.UUID, list[tuple[Account, App]]]:
    """Not-removed accounts of these people, with their apps."""
    if not person_ids:
        return {}
    rows = await session.execute(
        select(Account, App)
        .join(App, App.id == Account.app_id)
        .where(Account.person_id.in_(person_ids), Account.status != AccountStatus.REMOVED)
        .order_by(App.name)
    )
    grouped: dict[uuid.UUID, list[tuple[Account, App]]] = defaultdict(list)
    for account, app in rows:
        grouped[account.person_id].append((account, app))
    return grouped


def _list_item(
    person: Person, accounts: list[tuple[Account, App]], converter: Converter, manager: Person | None
) -> PersonListItem:
    apps = {app.id: app for _, app in accounts}
    costs = [account_cost(account, app) for account, app in accounts]
    return PersonListItem(
        id=person.id,
        first_name=person.first_name,
        last_name=person.last_name,
        primary_email=person.primary_email,
        employee_code=person.employee_code,
        status=person.status,
        left_at=person.left_at,
        kind=person.kind,
        kind_source=person.kind_source,
        kind_reason=person.kind_reason,
        department=person.department,
        job_title=person.job_title,
        manager=person_ref(manager),
        manager_source=person.manager_source,
        accounts_count=len(accounts),
        apps=[app_ref(app) for app in sorted(apps.values(), key=lambda app: app.name.lower())],
        monthly_cost=money_list(sum_by_currency(costs)),
        monthly_cost_total=money(converter.total(costs)),
        created_at=person.created_at,
        updated_at=person.updated_at,
    )
