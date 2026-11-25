import uuid
from enum import StrEnum

from pydantic import BaseModel, Field


class ImportRowAction(StrEnum):
    CREATE = "create"
    UPDATE = "update"
    UNCHANGED = "unchanged"
    ERROR = "error"


class FieldChange(BaseModel):
    field: str
    old: str | None
    new: str | None


class ImportRowResult(BaseModel):
    line: int = Field(description="Line number in the file; the header is line 1")
    email: str | None
    action: ImportRowAction
    person_id: uuid.UUID | None = Field(description="Existing person (update, unchanged) or the created one")
    changes: list[FieldChange]
    errors: list[str]
    first_name: str | None = Field(default=None, description="create rows: the new person's first name")
    last_name: str | None = Field(default=None, description="create rows: the new person's last name")
    employee_code: str | None = Field(default=None, description="create rows: the new person's employee code")
    aliases: list[str] = Field(default_factory=list, description="create rows: the new person's aliases")


class ImportResult(BaseModel):
    """With ``dry_run`` nothing is saved and the counts say what would happen."""

    dry_run: bool
    created: int
    updated: int
    unchanged: int
    failed: int
    rows: list[ImportRowResult]
