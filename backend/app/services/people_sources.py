"""People sources without a connector and the links that say where a person comes from."""

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import select

from app.models import App, Connection, PeopleSource, PersonLink
from app.models.enums import PeopleSourceKind, PersonLinkSource

if TYPE_CHECKING:
    import uuid

    from sqlalchemy.ext.asyncio import AsyncSession

DEFAULT_SOURCE_NAMES = {PeopleSourceKind.MANUAL: "Manual entry", PeopleSourceKind.CSV: "CSV import"}


async def get_or_create_source(session: AsyncSession, kind: PeopleSourceKind) -> PeopleSource:
    name = DEFAULT_SOURCE_NAMES[kind]
    source = await session.scalar(select(PeopleSource).where(PeopleSource.kind == kind, PeopleSource.name == name))
    if source is None:
        source = PeopleSource(kind=kind, name=name)
        session.add(source)
        await session.flush()
    return source


async def upsert_link(
    session: AsyncSession,
    *,
    person_id: uuid.UUID,
    source_type: PersonLinkSource,
    source_id: uuid.UUID,
    external_id: str,
    raw: dict[str, Any] | None = None,
    is_active: bool = True,
) -> PersonLink:
    link = await session.scalar(
        select(PersonLink).where(
            PersonLink.source_type == source_type,
            PersonLink.source_id == source_id,
            PersonLink.external_id == external_id,
        )
    )
    if link is None:
        link = PersonLink(source_type=source_type, source_id=source_id, external_id=external_id)
        session.add(link)
    link.person_id = person_id
    link.is_active = is_active
    link.last_seen_at = datetime.now(UTC)
    if raw is not None:
        link.raw = raw
    await session.flush()
    return link


async def source_names(session: AsyncSession, links: list[PersonLink]) -> dict[uuid.UUID, str]:
    """Display name of each link's source: people_source name or the connection's app name."""
    connection_ids = {link.source_id for link in links if link.source_type == PersonLinkSource.CONNECTION}
    other_ids = {link.source_id for link in links if link.source_type != PersonLinkSource.CONNECTION}
    names: dict[uuid.UUID, str] = {}
    if other_ids:
        rows = await session.execute(select(PeopleSource.id, PeopleSource.name).where(PeopleSource.id.in_(other_ids)))
        names.update({source_id: name for source_id, name in rows})
    if connection_ids:
        rows = await session.execute(
            select(Connection.id, App.name)
            .join(App, App.id == Connection.app_id)
            .where(Connection.id.in_(connection_ids))
        )
        names.update({source_id: name for source_id, name in rows})
    return names
