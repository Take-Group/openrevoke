import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import ForeignKey, LargeBinary, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.columns import created_at_column, enum_column, timestamp, uuid_pk
from app.models.enums import ActionKind, ActionReason, ActionStatus


class Action(Base):
    """A write to an app (create or delete an account) or a manual task."""

    __tablename__ = "action"

    id: Mapped[uuid.UUID] = uuid_pk()
    kind: Mapped[ActionKind] = enum_column(ActionKind, "kind", nullable=False)
    person_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("person.id", ondelete="SET NULL"), index=True
    )
    app_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("app.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    account_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("account.id", ondelete="SET NULL"), index=True
    )
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict, server_default="{}")
    status: Mapped[ActionStatus] = enum_column(
        ActionStatus, "status", nullable=False, default=ActionStatus.PENDING_APPROVAL, index=True
    )
    reason: Mapped[ActionReason] = enum_column(ActionReason, "reason", nullable=False)
    batch_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), index=True)
    approved_at: Mapped[datetime | None] = timestamp()
    started_at: Mapped[datetime | None] = timestamp()
    finished_at: Mapped[datetime | None] = timestamp()
    result: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    error: Mapped[str | None] = mapped_column(Text)
    # A one-time secret the write returned (Google's temporary password), Fernet-encrypted.
    # Shown once through POST /api/actions/{id}/reveal-secret, then wiped.
    secret_result_encrypted: Mapped[bytes | None] = mapped_column(LargeBinary)
    created_at: Mapped[datetime] = created_at_column()
