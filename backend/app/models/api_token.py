import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.columns import created_at_column, enum_column, timestamp, uuid_pk
from app.models.enums import ApiTokenScope
from app.models.user import User


class ApiToken(Base):
    """Personal API token of a panel user, for the REST API and the MCP server. Stores only the SHA-256.

    The token acts as its owner: the owner's role decides what it reaches, ``scope`` can narrow it to reads.
    """

    __tablename__ = "api_token"

    id: Mapped[uuid.UUID] = uuid_pk()
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("panel_user.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    # First characters of the token, shown in the panel so the owner can tell tokens apart.
    prefix: Mapped[str] = mapped_column(String(16), nullable=False)
    scope: Mapped[ApiTokenScope] = enum_column(ApiTokenScope, "api_token_scope", nullable=False)
    created_at: Mapped[datetime] = created_at_column()
    last_used_at: Mapped[datetime | None] = timestamp()

    user: Mapped[User] = relationship(lazy="joined")
