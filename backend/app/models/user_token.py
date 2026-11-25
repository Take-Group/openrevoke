import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.columns import created_at_column, enum_column, timestamp, uuid_pk
from app.models.enums import UserRole, UserTokenKind


class UserToken(Base):
    """One-time link an admin passes on: an invite to register or a password reset. Stores only the SHA-256."""

    __tablename__ = "user_token"

    id: Mapped[uuid.UUID] = uuid_pk()
    kind: Mapped[UserTokenKind] = enum_column(UserTokenKind, "user_token_kind", nullable=False)
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    email: Mapped[str] = mapped_column(String(320), nullable=False, index=True)
    # Password reset: the user. Invite: NULL until registration.
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("panel_user.id", ondelete="CASCADE"), index=True
    )
    # Invite only: the role the new user gets.
    role: Mapped[UserRole | None] = enum_column(UserRole, "user_token_role", nullable=True)
    created_by_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("panel_user.id", ondelete="SET NULL")
    )
    created_at: Mapped[datetime] = created_at_column()
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    used_at: Mapped[datetime | None] = timestamp()
