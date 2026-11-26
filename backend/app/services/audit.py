"""Append-only audit log. Every write in a service calls ``record``.

Every event also carries the app and the person it is about (``app_id``,
``person_id``), so the panel can show the history of one app or one person.
``record`` takes them as arguments or works them out from the entity and the
data (see ``_subjects``).
"""

import uuid
from typing import TYPE_CHECKING, Any

from sqlalchemy import Select, func, select

from app.models import Account, Action, AuditEvent, Connection
from app.services.auth.actor import current_actor

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

_OWNED_ENTITIES: dict[str, type[Account] | type[Action]] = {"account": Account, "action": Action}


async def record(
    session: AsyncSession,
    event: str,
    entity_type: str,
    entity_id: uuid.UUID | None,
    data: dict[str, Any] | None = None,
    *,
    app_id: uuid.UUID | None = None,
    person_id: uuid.UUID | None = None,
) -> AuditEvent:
    inferred_app, inferred_person = await _subjects(session, entity_type, entity_id, data or {})
    audit_event = AuditEvent(
        actor=current_actor.get(),  # the signed-in user's e-mail; "local" in workflows and the CLI
        event=event,
        entity_type=entity_type,
        entity_id=entity_id,
        data=data or None,
        app_id=app_id or inferred_app,
        person_id=person_id or inferred_person,
    )
    session.add(audit_event)
    await session.flush()
    return audit_event


async def _subjects(
    session: AsyncSession, entity_type: str, entity_id: uuid.UUID | None, data: dict[str, Any]
) -> tuple[uuid.UUID | None, uuid.UUID | None]:
    """App and person of an event: the entity itself, ids in ``data``, then the entity's row."""
    app_id = entity_id if entity_type == "app" else _uuid(data.get("app_id"))
    person_id = (
        entity_id if entity_type == "person" else _uuid(data.get("person_id")) or _uuid(data.get("previous_person_id"))
    )
    if entity_id is None or (app_id and person_id):
        return app_id, person_id
    model = _OWNED_ENTITIES.get(entity_type)
    if model is not None:
        row = await session.get(model, entity_id)  # usually already in the session, no query
        if row is not None:
            return app_id or row.app_id, person_id or row.person_id
    elif entity_type == "connection" and app_id is None:
        connection = await session.get(Connection, entity_id)
        app_id = connection.app_id if connection else None
    return app_id, person_id


def _uuid(value: object) -> uuid.UUID | None:
    if isinstance(value, uuid.UUID):
        return value
    if isinstance(value, str):
        try:
            return uuid.UUID(value)
        except ValueError:
            return None
    return None


async def list_events(
    session: AsyncSession,
    *,
    entity_type: str | None,
    entity_id: uuid.UUID | None,
    event: str | None,
    app_id: uuid.UUID | None = None,
    person_id: uuid.UUID | None = None,
    q: str | None,
    limit: int,
    offset: int,
) -> tuple[list[AuditEvent], int]:
    query = filtered(entity_type=entity_type, entity_id=entity_id, event=event, app_id=app_id, person_id=person_id, q=q)
    total = await session.scalar(select(func.count()).select_from(query.subquery()))
    rows = await session.scalars(query.order_by(AuditEvent.at.desc(), AuditEvent.id.desc()).limit(limit).offset(offset))
    return list(rows), total or 0


def filtered(
    *,
    entity_type: str | None = None,
    entity_id: uuid.UUID | None = None,
    event: str | None = None,
    app_id: uuid.UUID | None = None,
    person_id: uuid.UUID | None = None,
    q: str | None = None,
) -> Select[tuple[AuditEvent]]:
    """Events matching the filters of the panel's log, unordered."""
    query = select(AuditEvent)
    if entity_type:
        query = query.where(AuditEvent.entity_type == entity_type)
    if entity_id:
        query = query.where(AuditEvent.entity_id == entity_id)
    if event:
        query = query.where(AuditEvent.event == event)
    if app_id:
        query = query.where(AuditEvent.app_id == app_id)
    if person_id:
        query = query.where(AuditEvent.person_id == person_id)
    if q:
        query = query.where(AuditEvent.event.ilike(f"%{q}%"))
    return query
