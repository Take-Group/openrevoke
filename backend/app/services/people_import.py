"""CSV import of people.

Header ``email,first_name,last_name,employee_code,aliases,manager_email,department,job_title``;
only ``email`` is required. Aliases are separated with ``;``. Rows match existing people by
primary e-mail. Rules:

- a new person needs first_name and last_name,
- an empty cell never clears a value of an existing person,
- aliases are added, never removed,
- ``manager_email`` (primary e-mail or alias) names a person already stored or a row of the same
  file; anything else is a row error, and so is a self-manager or a loop (A -> B -> A). A manager
  from the file is set as ``manual``: an admin's list, which syncs keep,
- people missing from the file stay untouched,
- rows with errors are skipped, the rest is saved (with ``dry_run`` nothing is).
"""

import csv
import io
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from sqlalchemy import select

from app.models import Person, PersonEmail
from app.models.enums import ManagerSource, PeopleSourceKind, PersonLinkSource, PersonStatus
from app.schemas.people_import import FieldChange, ImportResult, ImportRowAction, ImportRowResult
from app.services import audit
from app.services.accounts import rematch_accounts
from app.services.errors import InvalidInputError
from app.services.matching import is_valid_email, normalize_email
from app.services.people_import_managers import resolve_managers
from app.services.people_sources import get_or_create_source, upsert_link

if TYPE_CHECKING:
    import uuid

    from sqlalchemy.ext.asyncio import AsyncSession

COLUMNS = ("email", "first_name", "last_name", "employee_code", "aliases", "manager_email", "department", "job_title")
HEADER = ",".join(COLUMNS)
MAX_BYTES = 2 * 1024 * 1024
MAX_ROWS = 10_000


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


def parse_csv(content: bytes) -> list[tuple[int, dict[str, str]]]:
    if len(content) > MAX_BYTES:
        raise InvalidInputError(f"The file is larger than {MAX_BYTES // (1024 * 1024)} MB")
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise InvalidInputError("The file must be UTF-8 encoded") from exc
    reader = csv.reader(io.StringIO(text))
    header = next(reader, None)
    if not header:
        raise InvalidInputError("The file is empty")
    columns = [name.strip().lower() for name in header]
    unknown = [name for name in columns if name not in COLUMNS]
    if unknown or "email" not in columns or len(set(columns)) != len(columns):
        raise InvalidInputError(
            f"Invalid header {','.join(header)!r}. Expected columns: {','.join(COLUMNS)} (only email is required)"
        )
    rows: list[tuple[int, dict[str, str]]] = []
    for values in reader:
        if not any(value.strip() for value in values):
            continue
        if len(rows) >= MAX_ROWS:
            raise InvalidInputError(f"The file has more than {MAX_ROWS} rows")
        cells = {name: (values[i].strip() if i < len(values) else "") for i, name in enumerate(columns)}
        rows.append((reader.line_num, cells))
    return rows


async def import_people(session: AsyncSession, content: bytes, *, dry_run: bool) -> ImportResult:
    rows = parse_csv(content)
    directory = await _load_directory(session)
    plans = [_plan_row(line, raw, directory) for line, raw in rows]
    resolve_managers(plans, directory)
    for plan in plans:
        if plan.person is not None and not plan.errors:
            _collect_changes(plan, directory)
        plan.decide()
    if not dry_run:
        await _apply(session, plans, directory)
    results = [_row_result(plan) for plan in plans]
    return ImportResult(
        dry_run=dry_run,
        created=sum(1 for plan in plans if plan.action == ImportRowAction.CREATE),
        updated=sum(1 for plan in plans if plan.action == ImportRowAction.UPDATE),
        unchanged=sum(1 for plan in plans if plan.action == ImportRowAction.UNCHANGED),
        failed=sum(1 for plan in plans if plan.action == ImportRowAction.ERROR),
        rows=results,
    )


def _row_result(plan: RowPlan) -> ImportRowResult:
    created = plan.action == ImportRowAction.CREATE
    return ImportRowResult(
        line=plan.line,
        email=plan.email or plan.raw.get("email") or None,
        action=plan.action,
        person_id=plan.person.id if plan.person else None,
        changes=plan.changes,
        errors=plan.errors,
        first_name=plan.first_name if created else None,
        last_name=plan.last_name if created else None,
        employee_code=plan.employee_code if created else None,
        aliases=list(plan.new_aliases) if created else [],
        manager_email=plan.manager if created else None,
        department=plan.department if created else None,
        job_title=plan.job_title if created else None,
    )


async def _load_directory(session: AsyncSession) -> Directory:
    people = list(await session.scalars(select(Person)))
    aliases = list(await session.scalars(select(PersonEmail)))
    aliases_of: dict[uuid.UUID, set[str]] = {}
    for alias in aliases:
        aliases_of.setdefault(alias.person_id, set()).add(alias.email)
    return Directory(
        by_email={person.primary_email: person for person in people},
        by_id={person.id: person for person in people},
        alias_owner={alias.email: alias.person_id for alias in aliases},
        aliases_of=aliases_of,
        code_owner={person.employee_code: person.id for person in people if person.employee_code},
    )


def _plan_row(line: int, raw: dict[str, str], directory: Directory) -> RowPlan:
    plan = RowPlan(line=line, raw=raw)
    email = normalize_email(raw.get("email"))
    if email is None or not is_valid_email(email):
        plan.errors.append(f"Invalid email: {raw.get('email', '')!r}")
        return plan
    plan.email = email
    if email in directory.file_emails:
        plan.errors.append(f"Duplicate email, already used on line {directory.file_emails[email]}")
        return plan
    directory.file_emails[email] = line
    plan.person = directory.by_email.get(email)
    person_id = plan.person.id if plan.person else None
    if plan.person is None and email in directory.alias_owner:
        plan.errors.append("This e-mail is an alias of another person")

    plan.first_name = raw.get("first_name") or None
    plan.last_name = raw.get("last_name") or None
    if plan.person is None and not (plan.first_name and plan.last_name):
        plan.errors.append("A new person needs first_name and last_name")

    code = raw.get("employee_code") or None
    if code:
        owner = directory.code_owner.get(code)
        if owner is not None and owner != person_id:
            plan.errors.append(f"Employee code {code} belongs to another person")
        elif code in directory.file_codes:
            plan.errors.append(f"Duplicate employee code, already used on line {directory.file_codes[code]}")
        else:
            directory.file_codes[code] = line
            plan.employee_code = code

    plan.department = (raw.get("department") or "")[:200] or None
    plan.job_title = (raw.get("job_title") or "")[:200] or None
    manager = raw.get("manager_email") or None
    if manager:
        plan.manager_email = normalize_email(manager)
        if plan.manager_email is None or not is_valid_email(plan.manager_email):
            plan.errors.append(f"Invalid manager_email: {manager!r}")

    current_aliases = directory.aliases_of.get(person_id, set()) if person_id else set()
    for value in (raw.get("aliases") or "").split(";"):
        alias = normalize_email(value)
        if alias is None or alias == email or alias in current_aliases or alias in plan.new_aliases:
            continue
        if not is_valid_email(alias):
            plan.errors.append(f"Invalid alias: {value.strip()!r}")
        elif alias in directory.by_email or alias in directory.alias_owner:
            plan.errors.append(f"Alias {alias} belongs to another person")
        elif alias in directory.file_emails:
            plan.errors.append(f"Alias {alias} is used on line {directory.file_emails[alias]}")
        else:
            directory.file_emails[alias] = line
            plan.new_aliases.append(alias)
    return plan


def _collect_changes(plan: RowPlan, directory: Directory) -> None:
    person = plan.person
    assert person is not None
    current_aliases = directory.aliases_of.get(person.id, set())
    for name in ("first_name", "last_name", "employee_code", "department", "job_title"):
        new = getattr(plan, name)
        old = getattr(person, name)
        if new is not None and new != old:
            plan.changes.append(FieldChange(field=name, old=old, new=new))
    if plan.new_aliases:
        plan.changes.append(
            FieldChange(
                field="aliases",
                old=", ".join(sorted(current_aliases)) or None,
                new=", ".join(sorted(current_aliases | set(plan.new_aliases))),
            )
        )
    current = directory.by_id.get(person.manager_id) if person.manager_id else None
    old_manager = current.primary_email if current else None
    if plan.manager is not None and plan.manager != old_manager:
        plan.changes.append(FieldChange(field="manager", old=old_manager, new=plan.manager))


async def _apply(session: AsyncSession, plans: list[RowPlan], directory: Directory) -> None:
    source = await get_or_create_source(session, PeopleSourceKind.CSV)
    touched: set[str] = set()
    for plan in plans:
        if plan.action == ImportRowAction.ERROR or plan.email is None:
            continue
        if plan.person is None:
            plan.person = Person(
                first_name=plan.first_name or "",
                last_name=plan.last_name or "",
                primary_email=plan.email,
                employee_code=plan.employee_code,
                department=plan.department,
                job_title=plan.job_title,
                status=PersonStatus.ACTIVE,
            )
            session.add(plan.person)
            await session.flush()
            await audit.record(
                session,
                "person.created",
                "person",
                plan.person.id,
                {
                    "primary_email": plan.email,
                    "aliases": plan.new_aliases,
                    "manager_email": plan.manager,
                    "via": "csv",
                    "line": plan.line,
                },
            )
            touched.add(plan.email)
        elif plan.changes:
            for change in plan.changes:
                if change.field not in ("aliases", "manager"):
                    setattr(plan.person, change.field, change.new)
            await audit.record(
                session,
                "person.updated",
                "person",
                plan.person.id,
                {
                    "changes": {change.field: {"old": change.old, "new": change.new} for change in plan.changes},
                    "via": "csv",
                    "line": plan.line,
                },
            )
        session.add_all(PersonEmail(person_id=plan.person.id, email=alias) for alias in plan.new_aliases)
        touched.update(plan.new_aliases)
        await upsert_link(
            session,
            person_id=plan.person.id,
            source_type=PersonLinkSource.CSV,
            source_id=source.id,
            external_id=plan.email,
            raw=plan.raw,
        )
    await session.flush()
    _apply_managers(plans, directory)
    await session.flush()
    await audit.record(
        session,
        "people.imported",
        "people_source",
        source.id,
        {
            "created": sum(1 for plan in plans if plan.action == ImportRowAction.CREATE),
            "updated": sum(1 for plan in plans if plan.action == ImportRowAction.UPDATE),
            "failed": sum(1 for plan in plans if plan.action == ImportRowAction.ERROR),
        },
    )
    await rematch_accounts(session, touched)


def _apply_managers(plans: list[RowPlan], directory: Directory) -> None:
    """After every row is stored: managers by primary e-mail (stored people and new rows alike)."""
    people = directory.by_email | {plan.email: plan.person for plan in plans if plan.person is not None and plan.email}
    for plan in plans:
        if plan.action == ImportRowAction.ERROR or plan.manager is None or plan.person is None:
            continue
        manager = people.get(plan.manager)
        if manager is not None and plan.person.manager_id != manager.id:
            plan.person.manager_id = manager.id
            plan.person.manager_source = ManagerSource.MANUAL  # an admin's list: syncs keep it
