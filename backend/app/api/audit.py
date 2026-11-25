import uuid

from fastapi import APIRouter

from app.api.deps import SessionDep
from app.api.params import DEFAULT_LIMIT, Limit, Offset, SearchQuery
from app.schemas.audit import AuditEventOut, AuditEventPage
from app.services import audit

router = APIRouter(prefix="/audit")


@router.get("", response_model=AuditEventPage)
async def list_audit_events(
    session: SessionDep,
    q: SearchQuery = None,
    entity_type: str | None = None,
    entity_id: uuid.UUID | None = None,
    event: str | None = None,
    app_id: uuid.UUID | None = None,
    person_id: uuid.UUID | None = None,
    limit: Limit = DEFAULT_LIMIT,
    offset: Offset = 0,
) -> AuditEventPage:
    """Newest first. ``q`` searches event names. ``app_id`` and ``person_id`` give the history of one
    app or one person (events about its accounts and actions included)."""
    events, total = await audit.list_events(
        session,
        entity_type=entity_type,
        entity_id=entity_id,
        event=event,
        app_id=app_id,
        person_id=person_id,
        q=q,
        limit=limit,
        offset=offset,
    )
    return AuditEventPage(items=[AuditEventOut.model_validate(item) for item in events], total=total)
