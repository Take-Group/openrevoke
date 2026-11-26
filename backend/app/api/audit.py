import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Response

from app.api.deps import SessionDep
from app.api.params import DEFAULT_LIMIT, Limit, Offset, SearchQuery
from app.schemas.audit import AuditEventOut, AuditEventPage
from app.services import audit, audit_export

router = APIRouter(prefix="/audit")

_MEDIA_TYPES = {"csv": "text/csv", "jsonl": "application/x-ndjson"}


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


@router.get(
    "/export",
    response_class=Response,
    responses={200: {"content": {"text/csv": {}, "application/x-ndjson": {}}}},
)
async def export_audit_events(
    session: SessionDep,
    format: audit_export.ExportFormat = "csv",  # noqa: A002 - the query parameter's public name
    q: SearchQuery = None,
    entity_type: str | None = None,
    entity_id: uuid.UUID | None = None,
    event: str | None = None,
    app_id: uuid.UUID | None = None,
    person_id: uuid.UUID | None = None,
    since: datetime | None = None,
) -> Response:
    """The log as CSV or JSON Lines, oldest first, same filters as the list, at most 100 000 rows.
    ``since`` (exclusive) continues after the last row of an earlier export."""
    body = await audit_export.export(
        session,
        format,
        entity_type=entity_type,
        entity_id=entity_id,
        event=event,
        app_id=app_id,
        person_id=person_id,
        q=q,
        since=since,
    )
    name = f"audit-log-{datetime.now(UTC):%Y-%m-%d}.{format}"
    return Response(
        content=body,
        media_type=_MEDIA_TYPES[format],
        headers={"Content-Disposition": f'attachment; filename="{name}"'},
    )
