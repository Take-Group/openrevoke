"""Database commands. The schema comes from the Alembic migrations in ``backend/migrations``.

python -m app.db migrate           apply missing migrations (container start)
python -m app.db migrate --seed    the same, and seed when there are no panel users yet (local stack)
python -m app.db reset             development: drop everything, migrate from zero, seed
python -m app.db seed              add the development data to an empty database
"""

import argparse
import asyncio
import sys

from app.database import engine
from app.db import schema
from app.db.seed import seed
from app.db.seed_google import start_seed_syncs
from app.redis import redis_client


async def _reconcile_schedules() -> None:
    """Drop the Temporal schedules of connections that no longer exist."""
    from app.temporal.worker import reconcile_schedules

    await reconcile_schedules()


async def _migrate() -> None:
    before = await schema.migrate()
    if before.pending:
        print(f"Database migrated from {before.current or 'empty'} to {before.head} ({before.pending} revisions).")


async def _main(args: argparse.Namespace) -> int:
    try:
        if args.command == "reset":
            await schema.drop()
            await _migrate()
            await redis_client.flushdb()  # sign-in tickets, rate limits and locks of the old data
            await seed()
            await _reconcile_schedules()
            await start_seed_syncs()
            print("Database reset and seeded.")
        elif args.command == "migrate":
            await _migrate()
            if args.seed and not await schema.has_users():
                await seed()
                await start_seed_syncs()
                print("Database seeded.")
        else:
            if await schema.has_users():
                print("The database already has data. Use reset.", file=sys.stderr)
                return 1
            await seed()
            print("Database seeded.")
        return 0
    except schema.SchemaError as exc:
        print(f"Database: {exc}", file=sys.stderr)
        return 2
    finally:
        await redis_client.aclose()
        await engine.dispose()


def main() -> None:
    parser = argparse.ArgumentParser(prog="python -m app.db", description="Open Revoke database")
    commands = parser.add_subparsers(dest="command", required=True)
    migrate = commands.add_parser("migrate", help="apply missing migrations")
    migrate.add_argument("--seed", action="store_true", help="seed when there are no panel users (development)")
    commands.add_parser("reset", help="development: drop the whole schema, migrate from zero and seed")
    commands.add_parser("seed", help="seed an empty database")
    sys.exit(asyncio.run(_main(parser.parse_args())))


main()
