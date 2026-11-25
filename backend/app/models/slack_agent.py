from datetime import UTC, datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, Integer, LargeBinary, String, Text, func, text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.columns import enum_column, timestamp
from app.models.enums import SlackAgentStatus


class SlackAgent(Base):
    """The Slack app of this instance and the state of its connection. One row (id = 1).

    ``secrets_encrypted`` is one Fernet-encrypted JSON object (``app.services.secret_box``) with
    ``bot_token`` (xoxb), ``app_token`` (xapp, Socket Mode), ``client_secret`` and the app
    configuration tokens (``config_token``, ``config_refresh_token``, ``config_token_expires_at``).
    """

    __tablename__ = "slack_agent"
    __table_args__ = (CheckConstraint("id = 1", name="single_row"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default=text("true"))
    bot_name: Mapped[str] = mapped_column(String(80), nullable=False)
    app_id: Mapped[str | None] = mapped_column(String(32))
    client_id: Mapped[str | None] = mapped_column(String(64))
    team_id: Mapped[str | None] = mapped_column(String(32))
    team_name: Mapped[str | None] = mapped_column(String(200))
    bot_user_id: Mapped[str | None] = mapped_column(String(32))
    secrets_encrypted: Mapped[bytes | None] = mapped_column(LargeBinary)
    avatar_set_at: Mapped[datetime | None] = timestamp()
    avatar_error: Mapped[str | None] = mapped_column(Text)
    status: Mapped[SlackAgentStatus] = enum_column(
        SlackAgentStatus, "status", nullable=False, default=SlackAgentStatus.NOT_CONFIGURED
    )
    last_error: Mapped[str | None] = mapped_column(Text)
    connected_at: Mapped[datetime | None] = timestamp()
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=lambda: datetime.now(UTC), nullable=False
    )
