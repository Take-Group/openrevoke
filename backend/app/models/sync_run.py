import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, Index, Integer, Text, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.columns import created_at_column, enum_column, timestamp, uuid_pk
from app.models.enums import SyncRunStatus


class SyncRun(Base):
    """One synchronization of a connection's accounts."""

    __tablename__ = "sync_run"
    __table_args__ = (Index("ix_sync_run_connection_started", "connection_id", "started_at"),)

    id: Mapped[uuid.UUID] = uuid_pk()
    connection_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("connection.id", ondelete="CASCADE"), nullable=False
    )
    started_at: Mapped[datetime] = created_at_column()
    finished_at: Mapped[datetime | None] = timestamp()
    status: Mapped[SyncRunStatus] = enum_column(SyncRunStatus, "status", nullable=False, default=SyncRunStatus.RUNNING)
    accounts_seen: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default=text("0"))
    accounts_added: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default=text("0"))
    accounts_removed: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default=text("0"))
    error: Mapped[str | None] = mapped_column(Text)
