import uuid

from sqlalchemy import CheckConstraint, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.columns import uuid_pk


class PersonEmail(Base):
    """An alias e-mail of a person, used to match accounts."""

    __tablename__ = "person_email"
    __table_args__ = (CheckConstraint("email = lower(btrim(email))", name="email_normalized"),)

    id: Mapped[uuid.UUID] = uuid_pk()
    person_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("person.id", ondelete="CASCADE"), nullable=False, index=True
    )
    email: Mapped[str] = mapped_column(String(320), nullable=False, unique=True)
