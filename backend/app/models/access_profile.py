import uuid
from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.columns import created_at_column, uuid_pk


class AccessProfile(Base):
    """A named set of apps with a role in each ("Developer", "Sales"): what a person in that role gets.

    Assigning a profile to a person creates onboarding actions for the apps they lack. Apps live in
    ``access_profile_app``, people in ``person_access_profile``.
    """

    __tablename__ = "access_profile"

    id: Mapped[uuid.UUID] = uuid_pk()
    name: Mapped[str] = mapped_column(String(200), nullable=False, unique=True)
    description: Mapped[str | None] = mapped_column(Text)
    # Requests for an app of this profile, from a person with the profile, skip the manager step.
    auto_approve_requests: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    created_at: Mapped[datetime] = created_at_column()
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=lambda: datetime.now(UTC), nullable=False
    )
