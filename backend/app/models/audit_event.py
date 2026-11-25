import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Index, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.columns import uuid_pk


class AuditEvent(Base):
    """Append-only log of every change. Code never updates or deletes rows."""

    __tablename__ = "audit_event"
    __table_args__ = (
        Index("ix_audit_event_entity", "entity_type", "entity_id"),
        Index("ix_audit_event_app_id", "app_id"),
        Index("ix_audit_event_person_id", "person_id"),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    actor: Mapped[str] = mapped_column(String(100), nullable=False)
    event: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False)
    entity_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    data: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    # The app and the person the event is about, for filtering. No foreign keys: the log outlives them.
    app_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    person_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
