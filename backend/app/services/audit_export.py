"""Export of the audit log for a company's own archive or SIEM: CSV or JSON Lines, oldest first.

Takes the same filters as the panel's log. ``MAX_ROWS`` keeps one response bounded; a larger
history is exported in parts with ``since`` (the ``at`` of the last row of the previous part).
"""

import csv
import io
import json
from typing import TYPE_CHECKING, Literal

from app.models import AuditEvent
from app.services import audit
from app.services.csv_cells import safe_cell

if TYPE_CHECKING:
    import uuid
    from datetime import datetime

    from sqlalchemy.ext.asyncio import AsyncSession

ExportFormat = Literal["csv", "jsonl"]
MAX_ROWS = 100_000
COLUMNS = ("at", "actor", "event", "entity_type", "entity_id", "app_id", "person_id", "data", "id")


async def export(
    session: AsyncSession,
    fmt: ExportFormat,
    *,
    entity_type: str | None = None,
    entity_id: uuid.UUID | None = None,
    event: str | None = None,
    app_id: uuid.UUID | None = None,
    person_id: uuid.UUID | None = None,
    q: str | None = None,
    since: datetime | None = None,
) -> str:
    query = audit.filtered(
        entity_type=entity_type, entity_id=entity_id, event=event, app_id=app_id, person_id=person_id, q=q
    )
    if since is not None:
        query = query.where(AuditEvent.at > since)
    rows = await session.scalars(query.order_by(AuditEvent.at, AuditEvent.id).limit(MAX_ROWS))
    records = [_record(row) for row in rows]
    if fmt == "jsonl":
        return "".join(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n" for record in records)
    out = io.StringIO()
    writer = csv.writer(out)
    writer.writerow(COLUMNS)
    for record in records:
        data = record["data"]
        cells = [
            json.dumps(data, ensure_ascii=False, sort_keys=True) if col == "data" and data else record[col]
            for col in COLUMNS
        ]
        writer.writerow([safe_cell(None if cell is None else str(cell)) for cell in cells])
    return out.getvalue()


def _record(row: AuditEvent) -> dict[str, object]:
    return {
        "id": str(row.id),
        "at": row.at.isoformat(),
        "actor": row.actor,
        "event": row.event,
        "entity_type": row.entity_type,
        "entity_id": str(row.entity_id) if row.entity_id else None,
        "app_id": str(row.app_id) if row.app_id else None,
        "person_id": str(row.person_id) if row.person_id else None,
        "data": row.data,
    }
