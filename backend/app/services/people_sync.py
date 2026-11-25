"""People from a connection that is a people source.

- A known link (same connection and external id) points to its person.
- Otherwise the person whose primary e-mail or alias equals the source's
  primary e-mail is linked. The source's aliases never match (see ``_find_person``).
- Otherwise a new person is created.
- Aliases from the source are only added, and only when nobody else uses them.
- Person or service account (``app.services.person_kind``): set for a new
  person, and checked again on every sync while ``kind_source = auto``; an
  admin's choice is never changed.
- Inactive in the source sets ``person_link.is_active = false``; the person's
  status never changes here. A person missing from the full list counts as
  inactive in the source.
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING

from sqlalchemy import select

from app.models import Person, PersonEmail, PersonLink
from app.models.enums import PersonKindSource, PersonLinkSource, PersonStatus
from app.services import audit, person_kind
from app.services.accounts import rematch_accounts
from app.services.matching import EmailIndex, is_valid_email, load_email_index, normalize_email
from app.services.people_sources import upsert_link

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from app.connectors.base import RemotePerson
    from app.models import Connection


@dataclass
class PeopleSyncStats:
    seen: int = 0
    created: int = 0
    linked: int = 0
    skipped: int = 0
    inactive: int = 0


async def apply_people(session: AsyncSession, connection: Connection, people: list[RemotePerson]) -> PeopleSyncStats:
    links = {
        link.external_id: link
        for link in await session.scalars(
            select(PersonLink).where(
                PersonLink.source_type == PersonLinkSource.CONNECTION, PersonLink.source_id == connection.id
            )
        )
    }
    index = await load_email_index(session)
    stats = PeopleSyncStats()
    seen: set[str] = set()
    touched: set[str] = set()
    for remote in people:
        email = normalize_email(remote.email)
        if not email or not is_valid_email(email) or not remote.external_id or remote.external_id in seen:
            stats.skipped += 1
            continue
        seen.add(remote.external_id)
        stats.seen += 1
        link = links.get(remote.external_id)
        person = await _find_person(session, index, link, email)
        created = person is None
        if person is None:
            person = await _create_person(session, connection, remote, email)
            index.primary[email] = person.id
            touched.add(email)
            stats.created += 1
        elif link is None:
            stats.linked += 1
        added = await _add_aliases(session, index, person, [email, *remote.aliases])
        code = await _fill_employee_code(session, person, remote.employee_code)
        kind = _apply_kind(person, remote, email)
        touched |= set(added)
        if not created and (added or code or kind):
            changes = (
                {"aliases_added": added} | ({"employee_code": code} if code else {}) | ({"kind": kind} if kind else {})
            )
            await audit.record(
                session,
                "person.updated",
                "person",
                person.id,
                {**changes, "via": "connection", "connection_id": str(connection.id)},
            )
        await upsert_link(
            session,
            person_id=person.id,
            source_type=PersonLinkSource.CONNECTION,
            source_id=connection.id,
            external_id=remote.external_id,
            raw=remote.raw or None,
            is_active=remote.active,
        )
        stats.inactive += 0 if remote.active else 1

    for external_id, link in links.items():
        if external_id not in seen and link.is_active:
            link.is_active = False
            stats.inactive += 1
    await session.flush()
    await rematch_accounts(session, touched)
    return stats


async def _find_person(session: AsyncSession, index: EmailIndex, link: PersonLink | None, email: str) -> Person | None:
    """Known link first, then the source's primary e-mail (a person's primary e-mail or alias).

    The source's aliases do not match: a leaver's address often becomes an alias of
    their manager, and matching on it would merge the manager into the leaver.
    """
    if link is not None:
        person = await session.get(Person, link.person_id)
        if person is not None:
            return person
    person_id = index.lookup(email).person_id
    return await session.get(Person, person_id) if person_id is not None else None


async def _create_person(session: AsyncSession, connection: Connection, remote: RemotePerson, email: str) -> Person:
    first_name = (remote.first_name or "").strip() or email.split("@", 1)[0]
    last_name = (remote.last_name or "").strip()
    person = Person(
        first_name=first_name[:200], last_name=last_name[:200], primary_email=email, status=PersonStatus.ACTIVE
    )
    session.add(person)
    await session.flush()
    await audit.record(
        session,
        "person.created",
        "person",
        person.id,
        {"primary_email": email, "via": "connection", "connection_id": str(connection.id)},
    )
    return person


def _apply_kind(person: Person, remote: RemotePerson, email: str) -> str | None:
    """Rules for people the admin did not set by hand. Returns the new kind when it changed."""
    if person.kind_source == PersonKindSource.MANUAL:
        return None
    kind, reason = person_kind.classify(
        email,
        remote.first_name,
        remote.last_name,
        last_sign_in_at=remote.last_sign_in_at,
        created_at=remote.created_at,
    )
    changed = person.kind != kind
    person.kind = kind
    person.kind_source = PersonKindSource.AUTO
    person.kind_reason = reason
    return str(kind) if changed else None


async def _add_aliases(session: AsyncSession, index: EmailIndex, person: Person, emails: list[str]) -> list[str]:
    added: list[str] = []
    for value in emails:
        email = normalize_email(value)
        if not email or not is_valid_email(email) or email == person.primary_email:
            continue
        if index.lookup(email).person_id is not None:
            continue  # already this person's alias, or someone else's e-mail
        session.add(PersonEmail(person_id=person.id, email=email))
        index.aliases[email] = person.id
        added.append(email)
    if added:
        await session.flush()
    return added


async def _fill_employee_code(session: AsyncSession, person: Person, code: str | None) -> str | None:
    """Set the employee code from the source when the person has none and nobody else uses it."""
    code = (code or "").strip()[:100] or None
    if code is None or person.employee_code is not None:
        return None
    if await session.scalar(select(Person.id).where(Person.employee_code == code)) is not None:
        return None
    person.employee_code = code
    await session.flush()
    return code
