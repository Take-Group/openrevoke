import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, ForeignKey, LargeBinary, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.columns import created_at_column, enum_column, timestamp, uuid_pk
from app.models.enums import ConnectionStatus


class Connection(Base):
    """How Open Revoke talks to an app: connector, config and encrypted secrets."""

    __tablename__ = "connection"

    id: Mapped[uuid.UUID] = uuid_pk()
    app_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("app.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    connector_key: Mapped[str] = mapped_column(String(100), nullable=False)
    config: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict, server_default="{}")
    secrets_encrypted: Mapped[bytes | None] = mapped_column(LargeBinary)
    is_people_source: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=text("false"))
    writes_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=text("false"))
    status: Mapped[ConnectionStatus] = enum_column(
        ConnectionStatus, "status", nullable=False, default=ConnectionStatus.NEVER_SYNCED
    )
    last_synced_at: Mapped[datetime | None] = timestamp()
    last_error: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = created_at_column()
