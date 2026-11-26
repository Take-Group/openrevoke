from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, Integer, String, text
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.columns import created_at_column, enum_column, timestamp
from app.models.enums import ChatPlatform, PasswordManager, PeopleImport


class Organization(Base):
    """The company this instance belongs to. One row (id = 1), written by the first-run setup."""

    __tablename__ = "organization"
    __table_args__ = (CheckConstraint("id = 1", name="single_row"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    # ISO 4217 code from app.services.currencies; the panel converts costs to it.
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    # IANA time zone (e.g. Europe/Warsaw). The panel shows dates and times in it.
    timezone: Mapped[str] = mapped_column(String(64), nullable=False, server_default="Europe/Warsaw")
    # Onboarding answers (skills/backend/setup-checklist.md): null until the admin picks on /welcome.
    people_import: Mapped[PeopleImport | None] = enum_column(PeopleImport, "people_import", nullable=True)
    chat_platform: Mapped[ChatPlatform | None] = enum_column(ChatPlatform, "chat_platform", nullable=True)
    # Which password manager the shared browser force-installs; null until the admin picks on /welcome.
    password_manager: Mapped[PasswordManager | None] = enum_column(PasswordManager, "password_manager", nullable=True)
    # Self sign-up on /signup (skills/backend/auth.md). Off: only invites create accounts.
    registration_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
    # On: an e-mail in one of ``registration_domains`` gets in at once, unconfirmed (the panel sends no mail);
    # everyone else waits for an admin.
    registration_auto_approve: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    registration_domains: Mapped[list[str]] = mapped_column(
        ARRAY(String(253)), nullable=False, server_default=text("'{}'")
    )
    # The admin closed the setup checklist on the dashboard.
    onboarding_dismissed_at: Mapped[datetime | None] = timestamp()
    created_at: Mapped[datetime] = created_at_column()
