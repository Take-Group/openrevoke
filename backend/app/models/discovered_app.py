import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.columns import created_at_column, enum_column, timestamp, uuid_pk
from app.models.enums import DiscoveredAppStatus


class DiscoveredApp(Base):
    """A third-party app people signed in to, found by a scan. One row per app name and connection.

    One app may use several OAuth clients (web, desktop, mobile); their ids are in ``client_ids``.
    """

    __tablename__ = "discovered_app"
    __table_args__ = (UniqueConstraint("connection_id", "key", name="uq_discovered_app_connection_key"),)

    id: Mapped[uuid.UUID] = uuid_pk()
    connection_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("connection.id", ondelete="CASCADE"), nullable=False
    )
    # Lowercased app name, or the client id when the app has no name.
    key: Mapped[str] = mapped_column(String(320), nullable=False)
    name: Mapped[str] = mapped_column(String(320), nullable=False)
    client_ids: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, default=list, server_default="[]")
    scopes: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, default=list, server_default="[]")
    status: Mapped[DiscoveredAppStatus] = enum_column(
        DiscoveredAppStatus, "status", nullable=False, default=DiscoveredAppStatus.NEW
    )
    app_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("app.id", ondelete="SET NULL"), index=True
    )
    first_seen_at: Mapped[datetime | None] = timestamp()
    last_seen_at: Mapped[datetime | None] = timestamp()
    created_at: Mapped[datetime] = created_at_column()
