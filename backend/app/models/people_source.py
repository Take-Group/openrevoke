import uuid
from datetime import datetime

from sqlalchemy import String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.columns import created_at_column, enum_column, uuid_pk
from app.models.enums import PeopleSourceKind


class PeopleSource(Base):
    """A source of people without a connector (manual entry, CSV import).

    A connector that lists people (e.g. Google Workspace) is a ``connection``
    with ``is_people_source = true`` instead.
    """

    __tablename__ = "people_source"
    __table_args__ = (UniqueConstraint("kind", "name", name="uq_people_source_kind_name"),)

    id: Mapped[uuid.UUID] = uuid_pk()
    kind: Mapped[PeopleSourceKind] = enum_column(PeopleSourceKind, "kind", nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    created_at: Mapped[datetime] = created_at_column()
