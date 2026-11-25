"""Database schema: Alembic migrations in ``backend/migrations``.

``migrate`` brings the database to the newest revision this image knows, under a PostgreSQL
advisory lock, so two processes starting at once do not migrate twice. It refuses a database
that a newer Open Revoke already migrated (the image does not know its revision) and a database
created before migrations existed (tables without ``alembic_version``).
"""

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from alembic import command
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import func, inspect, select, text

from app.database import async_session, engine
from app.models import User

if TYPE_CHECKING:
    from sqlalchemy.engine import Connection

ALEMBIC_INI = Path(__file__).resolve().parents[2] / "alembic.ini"
# Any constant shared by every process of the app: the key of the migration lock.
MIGRATION_LOCK = 7_316_402_815


class SchemaError(Exception):
    """The database cannot be migrated by this image; the message says what to do."""


@dataclass(frozen=True)
class SchemaState:
    current: str | None  # revision in the database, None for an empty database
    head: str  # newest revision this image knows
    pending: int  # revisions to apply


def _config() -> Config:
    return Config(str(ALEMBIC_INI))


def _script() -> ScriptDirectory:
    return ScriptDirectory.from_config(_config())


def _state(connection: Connection) -> SchemaState:
    script = _script()
    head = script.get_current_head()
    assert head is not None  # noqa: S101 - the image always ships the baseline revision
    current = MigrationContext.configure(connection).get_current_revision()
    if current is None:
        tables = set(inspect(connection).get_table_names()) - {"alembic_version"}
        if tables:
            raise SchemaError(
                "The database has tables but no migration history: it was created before Open Revoke "
                "had migrations. Development: `python -m app.db reset`. Installation: restore it into a "
                "fresh install or start with an empty database."
            )
        return SchemaState(current=None, head=head, pending=len(list(script.walk_revisions())))
    try:
        script.get_revision(current)
    except Exception as exc:  # noqa: BLE001 - alembic raises several types for an unknown revision
        raise SchemaError(
            f"The database is at revision {current}, which this Open Revoke does not know: a newer "
            "version migrated it. Update Open Revoke or restore the backup taken before the update."
        ) from exc
    pending = 0 if current == head else len(list(script.iterate_revisions(head, current)))
    return SchemaState(current=current, head=head, pending=pending)


def _upgrade(connection: Connection) -> SchemaState:
    connection.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": MIGRATION_LOCK})
    state = _state(connection)
    if state.pending:
        config = _config()
        config.attributes["connection"] = connection
        command.upgrade(config, "head")
    return state


async def migrate() -> SchemaState:
    """Apply the missing migrations. Returns the state before the upgrade."""
    async with engine.begin() as connection:
        return await connection.run_sync(_upgrade)


async def state() -> SchemaState:
    """Where the database is, without changing it (``python -m app.ops preflight``)."""
    async with engine.connect() as connection:
        return await connection.run_sync(_state)


async def drop() -> None:
    """Drop every table, type and sequence of the app: the whole ``public`` schema."""
    async with engine.begin() as connection:
        await connection.execute(text("DROP SCHEMA IF EXISTS public CASCADE"))
        await connection.execute(text("CREATE SCHEMA public"))


async def has_users() -> bool:
    async with async_session() as session:
        return bool(await session.scalar(select(func.count()).select_from(User)))
