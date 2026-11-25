import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.columns import created_at_column, enum_column, timestamp, uuid_pk
from app.models.enums import RecipeFixStatus


class RecipeFix(Base):
    """A local fix of one click recipe step (docs/browser-recipes.md, "Poprawki lokalne").

    Pinned to the step ``id``; the runner tries active fixes before the repo's candidates.
    ``within`` and ``target`` are locators with ``{{param}}`` placeholders, as in the recipe.
    """

    __tablename__ = "recipe_fix"
    __table_args__ = (Index("ix_recipe_fix_step", "recipe_app", "recipe_action", "status"),)

    id: Mapped[uuid.UUID] = uuid_pk()
    recipe_app: Mapped[str] = mapped_column(String(64), nullable=False)
    recipe_action: Mapped[str] = mapped_column(String(64), nullable=False)
    step_id: Mapped[str] = mapped_column(String(64), nullable=False)
    step_goal: Mapped[str] = mapped_column(Text, nullable=False, default="")
    irreversible: Mapped[bool] = mapped_column(nullable=False, default=False)
    within: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    target: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    status: Mapped[RecipeFixStatus] = enum_column(RecipeFixStatus, "status", nullable=False)
    author: Mapped[str] = mapped_column(String(200), nullable=False)
    # What the AI saw and chose: "instead of X, use Y (text of the element)".
    note: Mapped[str] = mapped_column(Text, nullable=False, default="")
    action_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("action.id", ondelete="SET NULL"), index=True
    )
    created_at: Mapped[datetime] = created_at_column()
    decided_at: Mapped[datetime | None] = timestamp()
