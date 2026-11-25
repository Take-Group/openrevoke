import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.columns import created_at_column, enum_column, timestamp, uuid_pk
from app.models.enums import AccountKind, AccountStatus, MatchMethod


class Account(Base):
    """An account in an app. ``person_id`` is null when nobody owns it yet."""

    __tablename__ = "account"
    __table_args__ = (
        UniqueConstraint("app_id", "external_id", name="uq_account_app_external"),
        Index("ix_account_app_status", "app_id", "status"),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    app_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("app.id", ondelete="RESTRICT"), nullable=False
    )
    connection_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("connection.id", ondelete="SET NULL"), index=True
    )
    external_id: Mapped[str] = mapped_column(String(320), nullable=False)
    email: Mapped[str | None] = mapped_column(String(320), index=True)
    username: Mapped[str | None] = mapped_column(String(320))
    display_name: Mapped[str | None] = mapped_column(String(320))
    role: Mapped[str | None] = mapped_column(String(100))
    status: Mapped[AccountStatus] = enum_column(AccountStatus, "status", nullable=False, default=AccountStatus.ACTIVE)
    person_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("person.id", ondelete="SET NULL"), index=True
    )
    match_method: Mapped[MatchMethod] = enum_column(
        MatchMethod, "match_method", nullable=False, default=MatchMethod.NONE
    )
    kind: Mapped[AccountKind] = enum_column(AccountKind, "kind", nullable=False, default=AccountKind.UNKNOWN)
    first_seen_at: Mapped[datetime] = created_at_column()
    last_seen_at: Mapped[datetime | None] = timestamp()
    removed_at: Mapped[datetime | None] = timestamp()
    raw: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
