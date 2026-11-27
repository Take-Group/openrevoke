"""Row plans and the directory of the people CSV import (``people_import``, ``people_import_managers``)."""

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from app.schemas.people_import import FieldChange, ImportRowAction

if TYPE_CHECKING:
    import uuid

    from app.models import Person


@dataclass
class RowPlan:
    line: int
    raw: dict[str, str]
    email: str | None = None
    person: Person | None = None
    first_name: str | None = None
    last_name: str | None = None
    employee_code: str | None = None
    department: str | None = None
    job_title: str | None = None
    # Manager e-mail as written in the file, then the manager's primary e-mail once resolved.
    manager_email: str | None = None
    manager: str | None = None
    new_aliases: list[str] = field(default_factory=list)
    changes: list[FieldChange] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    action: ImportRowAction = ImportRowAction.ERROR

    def decide(self) -> None:
        """Fix the row's action once planning is done (applying sets ``person`` on new rows)."""
        self.action = self._computed_action()

    def _computed_action(self) -> ImportRowAction:
        if self.errors:
            return ImportRowAction.ERROR
        if self.person is None:
            return ImportRowAction.CREATE
        return ImportRowAction.UPDATE if self.changes else ImportRowAction.UNCHANGED


@dataclass
class Directory:
    """Current people, aliases and codes, plus what earlier rows of the file claim."""

    by_email: dict[str, Person]
    by_id: dict[uuid.UUID, Person]
    alias_owner: dict[str, uuid.UUID]
    aliases_of: dict[uuid.UUID, set[str]]
    code_owner: dict[str, uuid.UUID]
    file_emails: dict[str, int] = field(default_factory=dict)
    file_codes: dict[str, int] = field(default_factory=dict)
