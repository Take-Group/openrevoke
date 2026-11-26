import uuid
from datetime import datetime

from sqlalchemy import Boolean, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.columns import created_at_column, enum_column, timestamp, uuid_pk
from app.models.enums import AccessRequestChannel, AccessRequestStatus, RequestFallbackReason


class AccessRequest(Base):
    """A person asked for an account in an app: in Slack (the agent), on the panel's "My access" page or
    through the API.

    The app's ``request_policy`` decides who approves: the person's manager, an admin, both, or
    nobody. Every decision is an ``AccessRequestDecision`` row. The account itself comes from
    ``action`` (a ``create_account`` or a manual task), created once the manager step is done. For a
    Slack request the agent tells the person on Slack when the action ends (``notified_at``).
    """

    __tablename__ = "access_request"

    id: Mapped[uuid.UUID] = uuid_pk()
    person_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("person.id", ondelete="CASCADE"), nullable=False, index=True
    )
    app_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("app.id", ondelete="CASCADE"), nullable=False, index=True
    )
    action_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("action.id", ondelete="SET NULL"), index=True
    )
    channel: Mapped[AccessRequestChannel] = enum_column(
        AccessRequestChannel, "channel", nullable=False, default=AccessRequestChannel.SLACK
    )
    slack_user_id: Mapped[str | None] = mapped_column(String(32))  # Slack requests only
    slack_channel_id: Mapped[str | None] = mapped_column(String(32))
    message: Mapped[str | None] = mapped_column(Text)  # what the person wrote, for the admin
    justification: Mapped[str | None] = mapped_column(Text)  # why the person needs it (required for new requests)
    role: Mapped[str | None] = mapped_column(String(100))  # role asked for in the app, free text
    requested_by: Mapped[str | None] = mapped_column(String(320))  # actor: panel user e-mail, Slack, token name
    on_behalf: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    # The manager the request waits for (manager step), kept for the record after the step.
    approver_person_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("person.id", ondelete="SET NULL"), index=True
    )
    fallback_reason: Mapped[RequestFallbackReason | None] = enum_column(RequestFallbackReason, "fallback_reason")
    status: Mapped[AccessRequestStatus] = enum_column(
        AccessRequestStatus, "status", nullable=False, default=AccessRequestStatus.PENDING_ADMIN, index=True
    )
    created_at: Mapped[datetime] = created_at_column()
    closed_at: Mapped[datetime | None] = timestamp()
    notified_at: Mapped[datetime | None] = timestamp()  # the person heard the result on Slack (Slack requests)
    approvers_notified_at: Mapped[datetime | None] = timestamp()  # admins got the Approve / Reject message
