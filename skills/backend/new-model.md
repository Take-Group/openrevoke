# Skill: New Database Model

## What it does
Adds or changes a SQLAlchemy model and the Alembic migration that brings existing databases
to it. The models in `app/models/` describe the schema; the revisions in
`backend/migrations/versions/` change real databases. Installations update by running the
migrations at start (`docker/entrypoint.sh` → `python -m app.db migrate`), so a model change
without a migration breaks every existing install.

## Files involved
- `app/models/<module>.py` — model definition (create or change)
- `app/models/__init__.py` — import and export the model, so it is registered on
  `Base.metadata` (autogenerate reads it)
- `app/models/columns.py` — shared columns (`created_at_column`, `enum_column`)
- `migrations/versions/` — one revision per change, `alembic.ini` and `migrations/env.py`
  (async engine, settings `DATABASE_URL`)
- `app/db/schema.py` — `migrate` (upgrade head under an advisory lock, refuses a newer or
  pre-migration database), `state`, `drop`
- `app/db/__main__.py` — `python -m app.db migrate [--seed] | reset | seed`
- `app/db/seed.py`, `seed_demo.py` — fictional development data for the panel

## Flow
1. **Create or change the model** in `app/models/<module>.py` (SQLAlchemy 2 `Mapped` style)
   and export a new one in `app/models/__init__.py`.
2. **Generate the revision** in the dev stack:
   ```bash
   docker compose -f compose.dev.yaml exec api alembic revision --autogenerate -m "add tag"
   ```
3. **Read the file** and fix what autogenerate gets wrong:
   - a renamed column or table shows as drop + add, which deletes the data: replace it with
     `op.alter_column(..., new_column_name=...)` or `op.rename_table`;
   - enums are strings with a CHECK constraint (`native_enum=False`): a new enum value is not
     detected; drop and create the `ck_<table>_<enum>` constraint by hand;
   - a new NOT NULL column on a table with rows needs a `server_default` or a data step
     (`op.execute("UPDATE ...")`) before `nullable=False`;
   - never import app models or services in a migration: they change later, the old
     migration must keep working. Use `sa.table()` / plain SQL.
   - `downgrade()` stays empty: going back means restoring the backup `open-revoke update`
     takes before it migrates.
4. **Run it**: `docker compose -f compose.dev.yaml exec api python -m app.db reset` (drop,
   migrate from zero, seed) and `... exec api alembic check` (no difference left between the
   models and the migrations). For a change to data, also try `alembic upgrade head` on a
   database of the previous version.
5. **Changelog**: a migration is a MINOR release; add a line under `[Unreleased]`.
6. **Extend the seeder** (`app/db/seed.py`) when the panel needs rows of the new table.

## Example
```python
# app/models/tag.py
from datetime import datetime
from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base
from app.models.columns import created_at_column

class Tag(Base):
    __tablename__ = "tag"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), unique=True)
    created_at: Mapped[datetime] = created_at_column()
```

## How to extend
- Relationships with `relationship()` and `ForeignKey`; one model per file.
- Constraint names come from the naming convention in `app/database.py`; keep it, Alembic
  needs stable names to drop or change constraints later.
