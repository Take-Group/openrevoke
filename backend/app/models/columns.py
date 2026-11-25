"""Column helpers shared by all models: UUID keys, timestamps, enums, money."""

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, Numeric, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

if TYPE_CHECKING:
    from datetime import datetime
    from decimal import Decimal
    from enum import StrEnum

MONEY = Numeric(12, 2)


def uuid_pk() -> Mapped[uuid.UUID]:
    return mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)


def created_at_column() -> Mapped[datetime]:
    return mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


def timestamp(nullable: bool = True) -> Mapped[datetime | None]:
    return mapped_column(DateTime(timezone=True), nullable=nullable)


def enum_column(enum_cls: type[StrEnum], name: str, **kwargs) -> Mapped:
    """Varchar column with a CHECK constraint that stores the enum *values*."""
    return mapped_column(
        Enum(
            enum_cls,
            name=name,
            native_enum=False,
            create_constraint=True,
            length=32,
            values_callable=lambda members: [member.value for member in members],
            validate_strings=True,
        ),
        **kwargs,
    )


def money_column(nullable: bool = True) -> Mapped[Decimal | None]:
    return mapped_column(MONEY, nullable=nullable)
