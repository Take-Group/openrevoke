"""Accounts in bulk: a CSV for many apps, pasted e-mails for one app, people from discovery.

CSV header ``app,email,username,display_name,role,status,kind``: ``app`` (name, catalog slug or the
app's slug) and one of ``email``/``username``/``display_name`` are required. Rules:

- only apps without a connector (``integration = manual``): other apps get accounts from their sync,
- an unknown app is an error, or with ``create_apps`` a new manual app (named from the catalog when
  the value matches it),
- a row matches an account of the app by e-mail (lowercase), then by username; it updates the
  account, an empty cell never clears a value, and nothing is deleted,
- new accounts match people by e-mail, as a sync does,
- rows with errors are skipped, the rest is saved (with ``dry_run`` nothing is).
"""

import csv
import io
import re
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import select

from app.catalog.lookup import app_catalog
from app.models import Account, App, Person
from app.models.enums import AccountKind, AccountStatus, Integration, MatchMethod
from app.schemas.accounts import AccountImportNewApp, AccountImportResult, AccountImportRow
from app.schemas.apps import AppCreate
from app.schemas.people_import import FieldChange, ImportRowAction
from app.services import audit
from app.services.accounts import set_owner
from app.services.apps import add_app
from app.services.errors import ConflictError, InvalidInputError, NotFoundError
from app.services.matching import EmailIndex, is_valid_email, load_email_index, normalize_email
from app.services.presenters import person_ref

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

COLUMNS = ("app", "email", "username", "display_name", "role", "status", "kind")
IDENTITY = ("email", "username", "display_name")
STATUSES = {status.value: status for status in (AccountStatus.ACTIVE, AccountStatus.INVITED, AccountStatus.SUSPENDED)}
KINDS = {kind.value: kind for kind in (AccountKind.PERSON, AccountKind.SERVICE)}
MAX_BYTES = 2 * 1024 * 1024
MAX_ROWS = 10_000
_PASTE_SPLIT = re.compile(r"[\n\r,;]+")
_ANGLE = re.compile(r"<([^<>]+)>")


@dataclass
class Target:
    """The app a row goes to: one that exists, or one the import creates."""

    name: str
    app: App | None = None
    catalog_key: str | None = None

    @property
    def key(self) -> str:
        return str(self.app.id) if self.app else f"new:{self.name.lower()}"


@dataclass
class RowPlan:
    line: int
    label: str
    target: Target | None = None
    email: str | None = None
    username: str | None = None
    display_name: str | None = None
    role: str | None = None
    status: AccountStatus | None = None
    kind: AccountKind | None = None
    account: Account | None = None
    person_id: uuid.UUID | None = None
    method: MatchMethod = MatchMethod.NONE
    changes: list[FieldChange] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    created: bool = False  # the import made ``account``

    @property
    def action(self) -> ImportRowAction:
        if self.errors:
            return ImportRowAction.ERROR
        if self.account is None or self.created:
            return ImportRowAction.CREATE
        return ImportRowAction.UPDATE if self.changes else ImportRowAction.UNCHANGED


@dataclass
class Directory:
    """Apps and their accounts, people's e-mails, and what earlier rows already claimed."""

    apps: list[App]
    emails: EmailIndex
    accounts: dict[uuid.UUID, list[Account]] = field(default_factory=dict)
    new_targets: dict[str, Target] = field(default_factory=dict)
    seen: dict[tuple[str, str], int] = field(default_factory=dict)

    def find_app(self, value: str) -> App | None:
        lowered = value.strip().lower()
        for app in self.apps:
            if lowered in (app.name.lower(), app.slug, app.catalog_key):
                return app
        entry = app_catalog().resolve(value)
        if entry is None:
            return None
        return next(
            (app for app in self.apps if entry.slug == app.catalog_key or entry.name.lower() == app.name.lower()), None
        )

    def find_account(self, app: App, email: str | None, username: str | None) -> Account | None:
        accounts = self.accounts.get(app.id, [])
        if email:
            found = next((a for a in accounts if a.email == email or a.external_id.lower() == email), None)
            if found:
                return found
        if username:
            lowered = username.lower()
            return next((a for a in accounts if (a.username or "").lower() == lowered), None)
        return None


def _read_csv(content: bytes) -> tuple[list[str], list[tuple[int, list[str]]]]:
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
    rows: list[tuple[int, list[str]]] = []
    for values in reader:
        if not any(value.strip() for value in values):
            continue
        if len(rows) >= MAX_ROWS:
            raise InvalidInputError(f"The file has more than {MAX_ROWS} rows")
        rows.append((reader.line_num, values))
    return header, rows


def parse_csv(content: bytes) -> list[tuple[int, dict[str, str]]]:
    header, rows = _read_csv(content)
    columns = [name.strip().lower() for name in header]
    unknown = [name for name in columns if name not in COLUMNS]
    if unknown or "app" not in columns or not set(IDENTITY) & set(columns) or len(set(columns)) != len(columns):
        raise InvalidInputError(
            f"Invalid header {','.join(header)!r}. Expected columns: {','.join(COLUMNS)} "
            "(app and one of email, username, display_name are required)"
        )
    return [
        (line, {name: (values[i].strip() if i < len(values) else "") for i, name in enumerate(columns)})
        for line, values in rows
    ]


def parse_emails(text: str) -> list[str]:
    """One address per item; ``Name <a@b.com>`` gives ``a@b.com``."""
    items = []
    for part in _PASTE_SPLIT.split(text):
        match = _ANGLE.search(part)
        value = (match.group(1) if match else part).strip().strip("\"'")
        if value:
            items.append(value)
    if len(items) > MAX_ROWS:
        raise InvalidInputError(f"More than {MAX_ROWS} e-mails")
    return items


async def import_csv(session: AsyncSession, content: bytes, *, dry_run: bool, create_apps: bool) -> AccountImportResult:
    rows = parse_csv(content)
    directory = await _load(session)
    plans = [_plan_csv_row(line, raw, directory, create_apps) for line, raw in rows]
    return await _finish(session, directory, plans, dry_run=dry_run, via="csv")


async def import_emails(session: AsyncSession, app_id: uuid.UUID, text: str, *, dry_run: bool) -> AccountImportResult:
    """Pasted e-mails into one manual app."""
    app = await session.get(App, app_id)
    if app is None:
        raise NotFoundError("App not found")
    if app.integration != Integration.MANUAL:
        raise ConflictError(f"Accounts of {app.name} come from its connection: add them in the app, then sync")
    directory = await _load(session)
    target = Target(name=app.name, app=app)
    plans = []
    for position, value in enumerate(parse_emails(text), start=1):
        plan = RowPlan(line=position, label=app.name, target=target)
        _plan_account(plan, {"email": value}, directory)
        plans.append(plan)
    return await _finish(session, directory, plans, dry_run=dry_run, via="paste")


async def add_people_accounts(session: AsyncSession, app: App, emails: list[str], *, via: str) -> int:
    """Active person accounts for these e-mails in a manual app; existing ones stay. Returns how many were created."""
    if app.integration != Integration.MANUAL or not emails:
        return 0
    directory = await _load(session)
    target = Target(name=app.name, app=app)
    plans = []
    for position, email in enumerate(emails, start=1):
        plan = RowPlan(line=position, label=app.name, target=target)
        _plan_account(plan, {"email": email, "kind": AccountKind.PERSON.value}, directory)
        if plan.action == ImportRowAction.CREATE:
            plans.append(plan)
    result = await _finish(session, directory, plans, dry_run=False, via=via)
    return result.created


async def _load(session: AsyncSession) -> Directory:
    apps = list(await session.scalars(select(App)))
    directory = Directory(apps=apps, emails=await load_email_index(session))
    manual = [app.id for app in apps if app.integration == Integration.MANUAL]
    for account in await session.scalars(select(Account).where(Account.app_id.in_(manual))):
        directory.accounts.setdefault(account.app_id, []).append(account)
    return directory


def _plan_csv_row(line: int, raw: dict[str, str], directory: Directory, create_apps: bool) -> RowPlan:
    value = raw.get("app", "")
    plan = RowPlan(line=line, label=value)
    if not value:
        plan.errors.append("The app column is empty")
        return plan
    app = directory.find_app(value)
    if app is not None:
        if app.integration != Integration.MANUAL:
            plan.errors.append(f"Accounts of {app.name} are synced from the app")
            return plan
        plan.target = Target(name=app.name, app=app)
    elif create_apps:
        entry = app_catalog().resolve(value)
        name = entry.name if entry else value.strip()[:200]
        plan.target = directory.new_targets.setdefault(
            name.lower(), Target(name=name, catalog_key=entry.slug if entry else None)
        )
    else:
        plan.errors.append(f"Unknown app {value!r}: add it first or turn on creating missing apps")
        return plan
    _plan_account(plan, raw, directory)
    return plan


def _plan_account(plan: RowPlan, raw: dict[str, str], directory: Directory) -> None:
    raw_email = raw.get("email") or ""
    plan.email = normalize_email(raw_email)
    if plan.email and not is_valid_email(plan.email):
        plan.errors.append(f"Invalid email: {raw_email!r}")
    plan.username = raw.get("username") or None
    plan.display_name = raw.get("display_name") or None
    plan.role = (raw.get("role") or "")[:100] or None
    if not (plan.email or plan.username or plan.display_name):
        plan.errors.append("Give an email, username or display_name")
    status = (raw.get("status") or "").lower()
    if status and status not in STATUSES:
        plan.errors.append(f"Unknown status {status!r}: use active, invited or suspended")
    plan.status = STATUSES.get(status)
    kind = (raw.get("kind") or "").lower()
    if kind and kind not in KINDS:
        plan.errors.append(f"Unknown kind {kind!r}: use person or service")
    plan.kind = KINDS.get(kind)
    if plan.errors or plan.target is None:
        return
    identity = plan.email or (plan.username or "").lower()
    if identity:
        key = (plan.target.key, identity)
        if key in directory.seen:
            plan.errors.append(f"Same account as line {directory.seen[key]}")
            return
        directory.seen[key] = plan.line
    if plan.target.app is not None:
        plan.account = directory.find_account(plan.target.app, plan.email, plan.username)
    if plan.account is None:
        match = directory.emails.lookup(plan.email)
        plan.person_id, plan.method = match.person_id, match.method
    else:
        _collect_changes(plan, plan.account)


def _collect_changes(plan: RowPlan, account: Account) -> None:
    new_values = {
        "email": plan.email if not account.email else None,
        "username": plan.username,
        "display_name": plan.display_name,
        "role": plan.role,
        "status": plan.status,
        "kind": plan.kind,
    }
    for name, new in new_values.items():
        old = getattr(account, name)
        if new is not None and new != old:
            plan.changes.append(FieldChange(field=name, old=None if old is None else str(old), new=str(new)))


async def _finish(
    session: AsyncSession, directory: Directory, plans: list[RowPlan], *, dry_run: bool, via: str
) -> AccountImportResult:
    used_new = {
        plan.target.name.lower(): plan.target
        for plan in plans
        if plan.target and plan.target.app is None and not plan.errors
    }
    if not dry_run:
        await _apply(session, plans, list(used_new.values()), via)
    people = await _people(session, plans)
    return AccountImportResult(
        dry_run=dry_run,
        created=sum(1 for plan in plans if plan.action == ImportRowAction.CREATE),
        updated=sum(1 for plan in plans if plan.action == ImportRowAction.UPDATE),
        unchanged=sum(1 for plan in plans if plan.action == ImportRowAction.UNCHANGED),
        failed=sum(1 for plan in plans if plan.action == ImportRowAction.ERROR),
        rows=[_row(plan, people) for plan in plans],
        new_apps=[
            AccountImportNewApp(
                name=target.name, catalog_key=target.catalog_key, app_id=target.app.id if target.app else None
            )
            for target in used_new.values()
        ],
    )


async def _apply(session: AsyncSession, plans: list[RowPlan], new_targets: list[Target], via: str) -> None:
    for target in new_targets:
        target.app = await add_app(session, AppCreate(name=target.name, catalog_key=target.catalog_key))
        await audit.record(session, "app.created", "app", target.app.id, {"name": target.name, "via": via})
    now = datetime.now(UTC)
    counts: dict[uuid.UUID, dict[str, int]] = {}
    for plan in plans:
        if plan.errors or plan.target is None or plan.target.app is None:
            continue
        app = plan.target.app
        if plan.account is None:
            plan.account = Account(
                app_id=app.id,
                external_id=plan.email or plan.username or f"manual:{uuid.uuid4()}",
                email=plan.email,
                username=plan.username,
                display_name=plan.display_name,
                role=plan.role,
                status=plan.status or AccountStatus.ACTIVE,
                kind=plan.kind or AccountKind.UNKNOWN,
                last_seen_at=now,
            )
            set_owner(plan.account, plan.person_id, plan.method)
            session.add(plan.account)
            counts.setdefault(app.id, {"created": 0, "updated": 0})["created"] += 1
            plan.created = True
        elif plan.changes:
            for change in plan.changes:
                value = getattr(plan, change.field)
                setattr(plan.account, change.field, value)
                if change.field == "status":
                    plan.account.removed_at = None
            counts.setdefault(app.id, {"created": 0, "updated": 0})["updated"] += 1
    await session.flush()
    for app_id, count in counts.items():
        await audit.record(session, "accounts.imported", "app", app_id, {**count, "via": via})


async def _people(session: AsyncSession, plans: list[RowPlan]) -> dict[uuid.UUID, Person]:
    ids = {plan.person_id for plan in plans if plan.person_id}
    ids |= {plan.account.person_id for plan in plans if plan.account is not None and plan.account.person_id}
    if not ids:
        return {}
    return {person.id: person for person in await session.scalars(select(Person).where(Person.id.in_(ids)))}


def _row(plan: RowPlan, people: dict[uuid.UUID, Person]) -> AccountImportRow:
    account = plan.account
    person_id = account.person_id if account is not None and account.person_id else plan.person_id
    return AccountImportRow(
        line=plan.line,
        app=plan.target.name if plan.target else plan.label,
        app_id=plan.target.app.id if plan.target and plan.target.app else None,
        email=plan.email,
        username=plan.username,
        display_name=plan.display_name,
        action=plan.action,
        account_id=account.id if account is not None else None,
        person=person_ref(people.get(person_id)) if person_id else None,
        changes=plan.changes,
        errors=plan.errors,
    )
