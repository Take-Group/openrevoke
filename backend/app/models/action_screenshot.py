import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, LargeBinary, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.columns import created_at_column


class ActionScreenshot(Base):
    """Where a click recipe stopped: a PNG of the tab at the failed step, shown to admins.

    A separate table, so listing actions never loads the image. A retry deletes it.
    """

    __tablename__ = "action_screenshot"

    action_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("action.id", ondelete="CASCADE"), primary_key=True
    )
    png: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    url: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = created_at_column()
