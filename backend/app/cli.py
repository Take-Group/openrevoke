"""Admin commands for when the panel cannot help: a lost phone or no e-mail for a password reset.

In Docker::

    docker compose exec app /app/backend/.venv/bin/python -m app.cli list-users
    docker compose exec app /app/backend/.venv/bin/python -m app.cli reset-2fa admin@example.com
    docker compose exec app /app/backend/.venv/bin/python -m app.cli reset-link admin@example.com
    docker compose exec -it app /app/backend/.venv/bin/python -m app.cli set-password admin@example.com
    docker compose exec app /app/backend/.venv/bin/python -m app.cli setup-link
"""

import argparse
import asyncio
import getpass
import sys

from sqlalchemy import select

from app.database import async_session, engine
from app.models import User
from app.redis import redis_client
from app.services import audit
from app.services.auth import passwords, passwords_flow, sessions, setup_link, sign_in
from app.services.auth.actor import current_actor
from app.services.errors import InvalidInputError


async def _list_users() -> int:
    async with async_session() as session:
        for user in await session.scalars(select(User).order_by(User.created_at)):
            print(f"{user.email}\t{user.role}\t2fa={'on' if user.totp_enabled else 'off'}\t{user.name}")
    return 0


async def _change(email: str, *, reset_totp: bool, password: str | None) -> int:
    current_actor.set("cli")
    async with async_session() as session, session.begin():
        user = await session.scalar(select(User).where(User.email == email.strip().lower()))
        if user is None:
            print(f"No user with e-mail {email}", file=sys.stderr)
            return 1
        if reset_totp:
            user.totp_secret_encrypted = None
            user.totp_last_step = None
            await audit.record(session, "user.totp_reset", "user", user.id)
        if password is not None:
            user.password_hash = passwords.hash_password(password)
            await audit.record(session, "user.password_changed", "user", user.id)
        await sessions.revoke_all(session, user.id)
    print("Done. The user was signed out" + (" and sets up 2FA at the next sign-in." if reset_totp else "."))
    return 0


async def _reset_link(email: str) -> int:
    """Print a one-time reset link: proof of access to the server replaces the e-mail."""
    current_actor.set("cli")
    async with async_session() as session, session.begin():
        user = await session.scalar(select(User).where(User.email == email.strip().lower()))
        if user is None:
            print(f"No user with e-mail {email}", file=sys.stderr)
            return 1
        link, expires_at = await passwords_flow.issue_link(session, user, by="cli")
    print(f"Open this link to set a new password (works once, until {expires_at:%Y-%m-%d %H:%M} UTC):\n{link}")
    return 0


async def _setup_link() -> int:
    """A new link for the first-run setup; the previous one stops working."""
    async with async_session() as session:
        if not await sign_in.setup_required(session):
            print("The panel is already set up: sign in, or use reset-link for a lost password.", file=sys.stderr)
            return 1
    link = await setup_link.issue()
    print(f"Open this link to create the first admin (works until the setup is done or a new link is made):\n{link}")
    return 0


def _read_password() -> str:
    first = getpass.getpass("New password: ")
    if first != getpass.getpass("Repeat it: "):
        raise InvalidInputError("The passwords differ.")
    passwords.check_policy(first)
    return first


async def _main(args: argparse.Namespace) -> int:
    try:
        if args.command == "list-users":
            return await _list_users()
        if args.command == "setup-link":
            return await _setup_link()
        if args.command == "reset-link":
            return await _reset_link(args.email)
        if args.command == "reset-2fa":
            return await _change(args.email, reset_totp=True, password=None)
        return await _change(args.email, reset_totp=False, password=_read_password())
    except InvalidInputError as exc:
        print(exc.message, file=sys.stderr)
        return 1
    finally:
        await engine.dispose()
        await redis_client.aclose()


def main() -> None:
    parser = argparse.ArgumentParser(prog="python -m app.cli", description="Open Revoke panel users")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("list-users", help="list panel users")
    commands.add_parser("setup-link", help="print a new link for the first-run setup (fresh installation only)")
    for name, text in (
        ("reset-2fa", "turn 2FA off; the next sign-in sets it up again"),
        ("reset-link", "print a one-time link to set a new password (no e-mail needed)"),
        ("set-password", ""),
    ):
        command = commands.add_parser(name, help=text or "set a new password (asked interactively)")
        command.add_argument("email")
    sys.exit(asyncio.run(_main(parser.parse_args())))


if __name__ == "__main__":
    main()
