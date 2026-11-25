import uuid
from datetime import UTC, datetime

from sqlalchemy import CheckConstraint, DateTime, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.columns import created_at_column, enum_column, timestamp, uuid_pk
from app.models.enums import PersonKind, PersonKindSource, PersonStatus


class Person(Base):
    """A person in the company, or a service account (``kind``). Accounts in apps are matched to people."""

    __tablename__ = "person"
    __table_args__ = (CheckConstraint("primary_email = lower(btrim(primary_email))", name="email_normalized"),)

    id: Mapped[uuid.UUID] = uuid_pk()
    first_name: Mapped[str] = mapped_column(String(200), nullable=False)
    last_name: Mapped[str] = mapped_column(String(200), nullable=False)
    primary_email: Mapped[str] = mapped_column(String(320), nullable=False, unique=True)
    employee_code: Mapped[str | None] = mapped_column(String(100), unique=True)
    status: Mapped[PersonStatus] = enum_column(
        PersonStatus, "status", nullable=False, default=PersonStatus.ACTIVE, index=True
    )
    left_at: Mapped[datetime | None] = timestamp()
    kind: Mapped[PersonKind] = enum_column(PersonKind, "kind", nullable=False, default=PersonKind.HUMAN, index=True)
    kind_source: Mapped[PersonKindSource] = enum_column(
        PersonKindSource, "kind_source", nullable=False, default=PersonKindSource.AUTO
    )
    # Why the rules made it a service account, e.g. "generic address kontakt@"; null for people.
    kind_reason: Mapped[str | None] = mapped_column(String(200))
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = created_at_column()
    # Python-side onupdate: the new value is known without a reload (async sessions cannot lazy-load).
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=lambda: datetime.now(UTC), nullable=False
    )
