import uuid
from datetime import datetime

from sqlalchemy import BigInteger, LargeBinary, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.columns import created_at_column, enum_column, timestamp, uuid_pk
from app.models.enums import UserRole, UserStatus


class User(Base):
    """A person who signs in to the panel. Not a ``Person``: panel users and managed people are separate."""

    __tablename__ = "panel_user"

    id: Mapped[uuid.UUID] = uuid_pk()
    email: Mapped[str] = mapped_column(String(320), nullable=False, unique=True)  # stored lower case
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    role: Mapped[UserRole] = enum_column(UserRole, "user_role", nullable=False)
    # Self sign-up starts at ``pending`` unless its domain is auto-approved; setup and invites create ``active``.
    status: Mapped[UserStatus] = enum_column(UserStatus, "user_status", nullable=False, default=UserStatus.ACTIVE)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    # TOTP secret encrypted with OPEN_REVOKE_SECRET_KEY. NULL: 2FA not set up yet, the next sign-in enrolls it.
    totp_secret_encrypted: Mapped[bytes | None] = mapped_column(LargeBinary)
    # Last accepted TOTP time step: a code is accepted once (replay protection).
    totp_last_step: Mapped[int | None] = mapped_column(BigInteger)
    created_at: Mapped[datetime] = created_at_column()
    password_changed_at: Mapped[datetime | None] = timestamp()
    last_login_at: Mapped[datetime | None] = timestamp()
    approved_at: Mapped[datetime | None] = timestamp()  # self sign-up only: when an admin or the domain rule let in

    @property
    def totp_enabled(self) -> bool:
        return self.totp_secret_encrypted is not None
