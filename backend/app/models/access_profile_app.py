import uuid

from sqlalchemy import ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class AccessProfileApp(Base):
    """An app in an access profile, with the role the account gets there (free text, may be empty)."""

    __tablename__ = "access_profile_app"

    profile_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("access_profile.id", ondelete="CASCADE"), primary_key=True
    )
    app_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("app.id", ondelete="CASCADE"), primary_key=True, index=True
    )
    role: Mapped[str | None] = mapped_column(String(100))
