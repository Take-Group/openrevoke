# open-revoke/backend/app/db/

Schema migrations, development reset and seed. The schema changes only through Alembic revisions in `../../migrations/versions/` (skill `skills/backend/new-model.md`).

- `__init__.py`: docstring only.
- `__main__.py`: CLI `python -m app.db migrate [--seed] | reset | seed`; exit 2 when the database cannot be migrated; `reset` (development) = drop schema, migrate, flush Redis, seed, reconcile Temporal schedules, `start_seed_syncs`.
- `schema.py`: `migrate()` (upgrade head under `pg_advisory_xact_lock`), `state()` (`SchemaState`: current, head, pending; for `app.ops preflight`), `SchemaError` (database from a newer version or without migration history), `drop()`, `has_users()`.
- `seed.py`: `seed()`: organization, admin and user panel users, sample apps (`APPS` list), then a people source; add data for new features here.
- `seed_google.py`: `seed_google_workspace` creates the Google Workspace app and connection from `SEED_GOOGLE_*` (no Google call); `start_seed_syncs` queues the first sync and scan of the seeded people source.
- `seed_demo.py`: `seed_demo_directory`: without `SEED_GOOGLE_*` and with the fake connector, a fictional people source "Example Directory" (12 people at example.com).
