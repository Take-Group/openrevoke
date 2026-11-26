import uuid
from datetime import datetime

from sqlalchemy import Boolean, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.columns import created_at_column, enum_column, uuid_pk
from app.models.enums import DecisionOutcome, DecisionStep, DecisionVia


class AccessRequestDecision(Base):
    """One decision on an access request: who approved or rejected which step, when and why.

    Append-only, like ``audit_event``: the record of who let a person in. ``decided_by`` keeps the
    label (e-mail, "e-mail (Slack)", token name) when the panel user is gone or never existed.
    """

    __tablename__ = "access_request_decision"

    id: Mapped[uuid.UUID] = uuid_pk()
    request_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("access_request.id", ondelete="CASCADE"), nullable=False, index=True
    )
    step: Mapped[DecisionStep] = enum_column(DecisionStep, "step", nullable=False)
    decision: Mapped[DecisionOutcome] = enum_column(DecisionOutcome, "decision", nullable=False)
    decided_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("panel_user.id", ondelete="SET NULL")
    )
    decided_by: Mapped[str] = mapped_column(String(320), nullable=False)
    via: Mapped[DecisionVia] = enum_column(DecisionVia, "via", nullable=False)
    override: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    comment: Mapped[str | None] = mapped_column(Text)
    decided_at: Mapped[datetime] = created_at_column()
