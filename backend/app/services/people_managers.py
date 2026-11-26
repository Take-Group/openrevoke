"""Reporting lines: setting a person's manager, cycle checks, reports and people without a manager.

Rules shared by the panel, the CSV import and the people sync:

- nobody is their own manager, and the managers above a person never lead back to them (A -> B -> A);
- ``manager_source = manual`` (an admin in the panel or a CSV import) is never changed by a sync;
- the panel refuses a manager who left or is a service account; a sync takes the source's data as it is.

Who decides as a manager (panel user, fallback) is in ``app.services.access.managers``.
"""

from typing import TYPE_CHECKING

from sqlalchemy import exists, select
from sqlalchemy.orm import aliased

from app.models import Person
from app.models.enums import ManagerSource, PersonKind, PersonStatus
from app.services.errors import InvalidInputError

if TYPE_CHECKING:
    import uuid
    from collections.abc import Hashable, Mapping

    from sqlalchemy import ColumnElement
    from sqlalchemy.ext.asyncio import AsyncSession

# Longest chain of managers walked; real org charts are far shallower, a longer one is broken data.
MAX_DEPTH = 1000


def creates_cycle[K: Hashable](managers: Mapping[K, K | None], person: K, manager: K | None) -> bool:
    """True when ``manager`` is ``person`` or has ``person`` among the managers above them.

    ``managers`` maps a person to their manager (any key type: ids, e-mails). A chain that is
    already broken (a loop above, or deeper than ``MAX_DEPTH``) also counts as a cycle.
    """
    seen: set[K] = set()
    current = manager
    while current is not None:
        if current == person or current in seen or len(seen) >= MAX_DEPTH:
            return True
        seen.add(current)
        current = managers.get(current)
    return False


async def manager_map(session: AsyncSession) -> dict[uuid.UUID, uuid.UUID | None]:
    """Every person's manager id, for cycle checks in memory."""
    return dict((await session.execute(select(Person.id, Person.manager_id))).tuples().all())


async def set_manager(session: AsyncSession, person: Person, manager_id: uuid.UUID | None) -> Person | None:
    """An admin's choice in the panel: sets or clears the manager as ``manual``. 400 on a bad choice."""
    manager = None
    if manager_id is not None:
        manager = await session.get(Person, manager_id)
        if manager is None:
            raise InvalidInputError("Manager not found")
        if manager.id == person.id:
            raise InvalidInputError("A person cannot be their own manager")
        if manager.status == PersonStatus.LEFT:
            raise InvalidInputError(f"{_name(manager)} has left and cannot be a manager")
        if manager.kind == PersonKind.SERVICE:
            raise InvalidInputError(f"{manager.primary_email} is a service account and cannot be a manager")
        if creates_cycle(await manager_map(session), person.id, manager.id):
            raise InvalidInputError(
                f"{_name(manager)} reports to {_name(person)}, directly or through others: that would make a loop"
            )
    person.manager_id = manager_id
    person.manager_source = ManagerSource.MANUAL  # syncs keep the admin's choice, also an empty one
    return manager


async def reports_of(session: AsyncSession, person_id: uuid.UUID) -> list[Person]:
    """People whose manager is this person, active first, then by name."""
    return list(
        await session.scalars(
            select(Person)
            .where(Person.manager_id == person_id)
            .order_by(Person.status == PersonStatus.LEFT, Person.last_name, Person.first_name)
        )
    )


async def people_by_id(session: AsyncSession, ids: set[uuid.UUID]) -> dict[uuid.UUID, Person]:
    if not ids:
        return {}
    return {person.id: person for person in await session.scalars(select(Person).where(Person.id.in_(ids)))}


def without_manager_clause() -> ColumnElement[bool]:
    """People with no manager set (the ``No manager`` filter)."""
    return Person.manager_id.is_(None)


def needs_manager_clause() -> ColumnElement[bool]:
    """Active people with no manager who manage nobody either.

    The top of a reporting line (the CEO) has reports and no manager by design: their requests go
    to an admin, so they are not counted as missing data.
    """
    report = aliased(Person)
    return (
        Person.manager_id.is_(None)
        & (Person.kind == PersonKind.HUMAN)
        & (Person.status == PersonStatus.ACTIVE)
        & ~exists().where(report.manager_id == Person.id, report.status == PersonStatus.ACTIVE)
    )


def _name(person: Person) -> str:
    return f"{person.first_name} {person.last_name}".strip() or person.primary_email
