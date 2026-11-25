import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, ForeignKey, Index, Integer, Text, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.columns import created_at_column, enum_column, timestamp, uuid_pk
from app.models.enums import ScanRunStatus


class ScanRun(Base):
    """One app discovery scan of an identity provider connection (Google Workspace)."""

    __tablename__ = "scan_run"
    __table_args__ = (Index("ix_scan_run_connection_started", "connection_id", "started_at"),)

    id: Mapped[uuid.UUID] = uuid_pk()
    connection_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("connection.id", ondelete="CASCADE"), nullable=False
    )
    started_at: Mapped[datetime] = created_at_column()
    finished_at: Mapped[datetime | None] = timestamp()
    status: Mapped[ScanRunStatus] = enum_column(ScanRunStatus, "status", nullable=False, default=ScanRunStatus.RUNNING)
    # Audit log window that was read.
    events_from: Mapped[datetime | None] = timestamp()
    events_until: Mapped[datetime | None] = timestamp()
    users_scanned: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default=text("0"))
    apps_found: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default=text("0"))
    apps_new: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default=text("0"))
    grants_found: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default=text("0"))
    # Null until the scan ends; false when the token inventory scope was not delegated.
    token_inventory: Mapped[bool | None] = mapped_column(Boolean)
    notes: Mapped[list[Any] | None] = mapped_column(JSONB)
    error: Mapped[str | None] = mapped_column(Text)
