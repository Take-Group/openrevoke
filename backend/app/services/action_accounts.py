"""Accounts changed by a finished action: a verified write or a manual task closed by hand.

A created account belongs to the action's person by hand (``match_method =
manual``), so a later sync never re-matches it. A deleted account keeps its
row: ``removed``, or ``suspended`` when the app only suspends (Google Workspace).
"""

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import select

from app.models import Account
from app.models.enums import AccountKind, AccountStatus, MatchMethod
from app.services import audit
from app.services.accounts import set_owner

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from app.connectors.base import RemoteAccount
    from app.models import Action, Connection

REMOTE_FIELDS = ("email", "username", "display_name", "role")


async def add_manual_account(session: AsyncSession, action: Action) -> Account:
    """A manual create closed as done in an app without a connection: the account from the payload."""
    email = action.payload.get("email")
    account = await _find(session, action, email)
    now = datetime.now(UTC)
    if account is None:
        account = Account(app_id=action.app_id, external_id=email, first_seen_at=now, kind=AccountKind.PERSON)
        session.add(account)
    account.email = email
    account.role = action.payload.get("role") or account.role
    account.status = AccountStatus.ACTIVE
    account.removed_at = None
    account.last_seen_at = now
    return await _assign(session, action, account, via="manual_task")


async def apply_created(
    session: AsyncSession, action: Action, connection: Connection, remote: RemoteAccount
) -> Account:
    """Store the account the read confirmed and assign it to the action's person."""
    account = await session.scalar(
        select(Account).where(Account.app_id == action.app_id, Account.external_id == remote.external_id)
    )
    now = datetime.now(UTC)
    if account is None:
        account = Account(
            app_id=action.app_id, external_id=remote.external_id, first_seen_at=now, kind=AccountKind.PERSON
        )
        session.add(account)
    for field in REMOTE_FIELDS:
        setattr(account, field, getattr(remote, field))
    account.status = AccountStatus(remote.status)
    account.removed_at = None
    account.connection_id = connection.id
    account.last_seen_at = now
    account.raw = remote.raw
    return await _assign(session, action, account, via="action")


async def apply_deleted(session: AsyncSession, action: Action, remote: RemoteAccount | None) -> Account | None:
    """The read confirmed the deletion: gone (``removed``) or still listed as suspended."""
    account = await session.get(Account, action.account_id) if action.account_id else None
    if account is None:
        return None
    now = datetime.now(UTC)
    if remote is None:
        account.status = AccountStatus.REMOVED
        account.removed_at = now
        event = "account.removed"
    else:
        account.status = AccountStatus.SUSPENDED
        account.last_seen_at = now
        event = "account.suspended"
    await session.flush()
    await audit.record(session, event, "account", account.id, {"action_id": str(action.id), "via": "action"})
    return account


async def _find(session: AsyncSession, action: Action, email: str | None) -> Account | None:
    if not email:
        return None
    return await session.scalar(
        select(Account).where(
            Account.app_id == action.app_id, (Account.external_id == email) | (Account.email == email)
        )
    )


async def _assign(session: AsyncSession, action: Action, account: Account, *, via: str) -> Account:
    set_owner(account, action.person_id, MatchMethod.MANUAL if action.person_id else MatchMethod.NONE)
    await session.flush()
    action.account_id = account.id
    await session.flush()
    await audit.record(
        session,
        "account.created",
        "account",
        account.id,
        {
            "action_id": str(action.id),
            "email": account.email,
            "person_id": str(action.person_id) if action.person_id else None,
            "via": via,
        },
    )
    return account
