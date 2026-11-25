"""Commands for the host script `open-revoke` (install, update), run inside the app image.

The logic that depends on the version lives here, in the image, so a new image knows what it
needs; the script on the host stays thin (skills/backend/releases.md). Output is one JSON
object on stdout, so a POSIX shell script can read it without jq.

    python -m app.ops version      {"version": "0.1.0"}
    python -m app.ops preflight    settings, database, migrations to apply, write actions in flight; exit 1 when blocked
    python -m app.ops in-flight    {"actions_in_flight": 0}
"""

import argparse
import asyncio
import json
import sys

from sqlalchemy import text


def _print(data: dict) -> None:
    print(json.dumps(data))


async def _in_flight() -> int:
    from app.database import async_session
    from app.services.maintenance import actions_in_flight

    async with async_session() as session:
        return await actions_in_flight(session)


async def _preflight() -> int:
    """Can this image start on this installation? Settings load, the database answers and its
    migration history is one this image can continue (not newer, not from before migrations)."""
    try:
        from app.config import settings
    except Exception as exc:  # noqa: BLE001 - a missing or invalid variable in .env is the answer, not a crash
        _print({"ok": False, "problems": [f"settings: {exc}"]})
        return 1
    from app.database import async_session, engine
    from app.db import schema

    problems: list[str] = []
    in_flight = None
    migrations = None
    try:
        async with async_session() as session:
            await session.execute(text("SELECT 1"))
        in_flight = await _in_flight()
        state = await schema.state()
        migrations = {"current": state.current, "head": state.head, "pending": state.pending}
    except schema.SchemaError as exc:
        problems.append(f"migrations: {exc}")
    except Exception as exc:  # noqa: BLE001 - reported to the script, which stops the update
        problems.append(f"database: {exc}")
    finally:
        await engine.dispose()
    _print(
        {
            "ok": not problems,
            "version": settings.version,
            "actions_in_flight": in_flight,
            "migrations": migrations,
            "problems": problems,
        }
    )
    return 0 if not problems else 1


async def _main(command: str) -> int:
    if command == "version":
        from app.config import settings

        _print({"version": settings.version})
        return 0
    if command == "preflight":
        return await _preflight()
    from app.database import engine

    try:
        _print({"actions_in_flight": await _in_flight()})
    finally:
        await engine.dispose()
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(prog="python -m app.ops", description="Open Revoke install and update helpers")
    parser.add_argument("command", choices=["version", "preflight", "in-flight"])
    sys.exit(asyncio.run(_main(parser.parse_args().command)))


if __name__ == "__main__":
    main()
