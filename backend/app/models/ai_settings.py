from datetime import UTC, datetime

from sqlalchemy import CheckConstraint, DateTime, Integer, LargeBinary, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.columns import enum_column
from app.models.enums import AiProvider, AiReasoningEffort


class AiSettings(Base):
    """The language model of every AI feature. One row (id = 1), written from the panel settings."""

    __tablename__ = "ai_settings"
    __table_args__ = (CheckConstraint("id = 1", name="single_row"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    provider: Mapped[AiProvider] = enum_column(AiProvider, "provider", nullable=False, default=AiProvider.ANTHROPIC)
    model: Mapped[str] = mapped_column(String(200), nullable=False)
    # OpenAI-compatible endpoint for openrouter and custom; null means the provider's default.
    base_url: Mapped[str | None] = mapped_column(String(2000))
    # Null sends no effort: the provider's default for the model.
    reasoning_effort: Mapped[AiReasoningEffort | None] = enum_column(AiReasoningEffort, "reasoning_effort")
    api_key_encrypted: Mapped[bytes | None] = mapped_column(LargeBinary)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=lambda: datetime.now(UTC), nullable=False
    )
