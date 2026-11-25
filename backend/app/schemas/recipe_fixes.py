import uuid
from datetime import datetime

from pydantic import Field

from app.models.enums import RecipeFixStatus
from app.schemas.common import ApiModel


class RecipeFixOut(ApiModel):
    """A local fix of one click recipe step. ``active`` fixes are tried before the recipe's own candidates."""

    id: uuid.UUID
    recipe_app: str = Field(description="Connector key of the recipe, e.g. slack")
    recipe_action: str = Field(examples=["delete_account"])
    step_id: str
    step_goal: str
    irreversible: bool = Field(description="A proposed fix of an irreversible click waits for an admin")
    locator: str = Field(description="The element the fix finds, readable: role, name, container")
    status: RecipeFixStatus
    author: str = Field(description='"ai:<model>" or "admin"')
    note: str = Field(description="What was wrong and what the fix picks instead")
    action_id: uuid.UUID | None = Field(description="The action whose run made the fix")
    created_at: datetime
    decided_at: datetime | None


class RecipeFixList(ApiModel):
    items: list[RecipeFixOut]
    total: int
