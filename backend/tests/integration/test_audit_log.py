"""The audit log is append-only in the database (migration d79e72c25401) and exports cleanly."""

import json
import uuid

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from app.database import async_session
from app.services import audit, audit_export

pytestmark = pytest.mark.integration


async def test_rows_cannot_be_changed_or_deleted() -> None:
    marker = f"test.append_only.{uuid.uuid4().hex[:8]}"
    async with async_session() as session, session.begin():
        await audit.record(session, marker, "test", None, {"x": 1})
    for statement in (
        "UPDATE audit_event SET event = 'changed' WHERE event = :e",
        "DELETE FROM audit_event WHERE event = :e",
        "TRUNCATE audit_event",
    ):
        async with async_session() as session:
            with pytest.raises(DBAPIError, match="append-only"):
                await session.execute(text(statement), {"e": marker})
            await session.rollback()


async def test_export_formats() -> None:
    marker = f"test.export.{uuid.uuid4().hex[:8]}"
    async with async_session() as session, session.begin():
        await audit.record(session, marker, "test", None, {"note": "=HYPERLINK(1)"})
    async with async_session() as session:
        lines = (await audit_export.export(session, "jsonl", event=marker)).splitlines()
        csv_body = await audit_export.export(session, "csv", event=marker)
    assert [json.loads(line)["data"] for line in lines] == [{"note": "=HYPERLINK(1)"}]
    assert csv_body.splitlines()[0].startswith("at,actor,event")
    assert marker in csv_body
