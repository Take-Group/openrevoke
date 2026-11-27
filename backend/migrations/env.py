"""Alembic environment. Migrations run on the app's async engine (DATABASE_URL from the settings).

`python -m app.db migrate` passes its own connection (``config.attributes["connection"]``), so
the upgrade runs under the advisory lock it holds. The `alembic` command line opens one here.
Migrations never import the app models: a model changes later, an old migration must not.
Only autogenerate reads them, through ``target_metadata``.
"""

import asyncio
from typing import TYPE_CHECKING

from alembic import context

import app.models  # registers every model on Base.metadata
from app.database import engine

if TYPE_CHECKING:
    from sqlalchemy.engine import Connection

config = context.config
target_metadata = app.models.Base.metadata


def _run(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata, compare_type=True)
    with context.begin_transaction():
        context.run_migrations()


async def _run_async() -> None:
    async with engine.connect() as connection:
        await connection.run_sync(_run)
        await connection.commit()
    await engine.dispose()


if context.is_offline_mode():
    raise SystemExit("Offline (--sql) migrations are not supported.")

connection = config.attributes.get("connection")
if connection is None:
    asyncio.run(_run_async())
else:
    _run(connection)
