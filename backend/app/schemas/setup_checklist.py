from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.models.enums import ChatPlatform, PasswordManager, PeopleImport
from app.schemas.common import ApiModel


class OnboardingChoices(BaseModel):
    """The questions of ``/welcome``. A missing field keeps the earlier answer."""

    people_import: PeopleImport | None = None
    chat_platform: ChatPlatform | None = None
    password_manager: PasswordManager | None = None


class ChecklistItem(BaseModel):
    key: Literal["people", "chat", "apps"]
    title: str
    description: str
    href: str | None = Field(description="Panel page that does the step, null when there is nothing to open")
    action: str | None = Field(description="Label of the button that opens href")
    done: bool
    supported: bool = Field(description="False when Open Revoke cannot do the chosen option yet (Microsoft 365, Teams)")


class OnboardingOut(ApiModel):
    people_import: PeopleImport | None
    chat_platform: ChatPlatform | None
    password_manager: PasswordManager | None
    answered: bool = Field(description="Every question of /welcome has an answer")
    dismissed_at: datetime | None
    items: list[ChecklistItem]
    completed: int = Field(description="Items done")
