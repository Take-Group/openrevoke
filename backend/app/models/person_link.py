import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, ForeignKey, String, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.columns import enum_column, timestamp, uuid_pk
from app.models.enums import PersonLinkSource


class PersonLink(Base):
    """Where we know a person from.

    ``source_id`` points to ``people_source.id`` (manual, csv) or
    ``connection.id`` (connection), so it has no foreign key.
    ``is_active`` is false when the source reports the person as inactive.
    """

    __tablename__ = "person_link"
    __table_args__ = (
        UniqueConstraint("source_type", "source_id", "external_id", name="uq_person_link_source_external"),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    person_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("person.id", ondelete="CASCADE"), nullable=False, index=True
    )
    source_type: Mapped[PersonLinkSource] = enum_column(PersonLinkSource, "source_type", nullable=False)
    source_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    external_id: Mapped[str] = mapped_column(String(320), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default=text("true"))
    last_seen_at: Mapped[datetime | None] = timestamp()
    raw: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
