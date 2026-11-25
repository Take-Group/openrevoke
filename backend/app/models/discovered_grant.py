import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.columns import enum_column, timestamp, uuid_pk
from app.models.enums import DirectoryStatus


class DiscoveredGrant(Base):
    """A person who signed in to a discovered app. Evidence of use, not proof of a seat.

    The person is matched by e-mail when read (``app.services.discovery``), so people added
    after the scan match too.
    """

    __tablename__ = "discovered_grant"
    __table_args__ = (UniqueConstraint("discovered_app_id", "email", name="uq_discovered_grant_app_email"),)

    id: Mapped[uuid.UUID] = uuid_pk()
    discovered_app_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("discovered_app.id", ondelete="CASCADE"), nullable=False
    )
    email: Mapped[str] = mapped_column(String(320), nullable=False, index=True)
    directory_status: Mapped[DirectoryStatus] = enum_column(
        DirectoryStatus, "directory_status", nullable=False, default=DirectoryStatus.ACTIVE
    )
    # When the directory deleted the person (audit log), if the scan saw it.
    deleted_at: Mapped[datetime | None] = timestamp()
    first_seen_at: Mapped[datetime | None] = timestamp()
    last_seen_at: Mapped[datetime | None] = timestamp()
    # Null when the last scan could not read the token inventory.
    token_active: Mapped[bool | None] = mapped_column(Boolean)
    scopes: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, default=list, server_default="[]")
    updated_at: Mapped[datetime | None] = timestamp()
