"""Store a full account list from a connector: upsert, match to people, detect removed accounts."""

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import select

from app.models import Account
from app.models.enums import AccountKind, AccountStatus
from app.services import audit
from app.services.accounts import set_owner
from app.services.matching import load_email_index, resolve_match
from app.services.sync_rules import RemovalThresholdError, exceeds_removal_threshold, missing_ids

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from app.models import Connection
    from app.services.sync_rules import CleanAccount

TRACKED_FIELDS = ("email", "username", "display_name", "role", "status")


@dataclass
class AccountSyncStats:
    seen: int = 0
    added: int = 0
    removed: int = 0


async def apply_accounts(
    session: AsyncSession, connection: Connection, remote: list[CleanAccount], *, force: bool = False
) -> AccountSyncStats:
    """Apply the full list. Raises ``RemovalThresholdError`` before writing anything when too many vanish.

    Manual owner assignments (``match_method = manual``) are never changed.
    """
    existing = {
        account.external_id: account
        for account in await session.scalars(select(Account).where(Account.app_id == connection.app_id))
    }
    live_ids = {external_id for external_id, account in existing.items() if account.status != AccountStatus.REMOVED}
    missing = missing_ids(live_ids, {account.external_id for account in remote})
    if not force and exceeds_removal_threshold(len(missing), len(live_ids)):
        raise RemovalThresholdError(len(missing), len(live_ids))

    stats = AccountSyncStats(seen=len(remote))
    index = await load_email_index(session)
    now = datetime.now(UTC)
    for item in remote:
        account = existing.get(item.external_id)
        if account is None:
            account = Account(
                app_id=connection.app_id,
                external_id=item.external_id,
                kind=AccountKind.UNKNOWN,
                first_seen_at=now,
            )
            _copy(account, item)
            session.add(account)
            event, data = "account.discovered", {"email": item.email, "username": item.username}
            stats.added += 1
        elif account.status == AccountStatus.REMOVED:
            _copy(account, item)
            account.removed_at = None
            event, data = "account.reappeared", {"email": item.email, "username": item.username}
            stats.added += 1
        else:
            changes = _copy(account, item)
            event, data = ("account.changed_in_app", {"changes": changes}) if changes else (None, None)
        account.connection_id = connection.id
        account.last_seen_at = now
        account.raw = item.raw

        previous_owner = account.person_id
        match = resolve_match(index, account.email, account.person_id, account.match_method)
        owner_changed = set_owner(account, match.person_id, match.method)
        await session.flush()
        if event:
            await audit.record(session, event, "account", account.id, {**data, "app_id": str(connection.app_id)})
        if owner_changed and previous_owner != account.person_id:
            await audit.record(
                session,
                "account.matched" if account.person_id else "account.unmatched",
                "account",
                account.id,
                {"person_id": _str(account.person_id), "previous_person_id": _str(previous_owner), "via": "sync"},
            )

    for external_id in sorted(missing):
        account = existing[external_id]
        account.status = AccountStatus.REMOVED
        account.removed_at = now
        stats.removed += 1
        await session.flush()
        await audit.record(
            session,
            "account.removed_detected",
            "account",
            account.id,
            {"app_id": str(connection.app_id), "email": account.email, "username": account.username, "forced": force},
        )
    return stats


def _copy(account: Account, item: CleanAccount) -> dict[str, dict[str, Any]]:
    """Copy the app's fields onto the account and return what changed."""
    changes: dict[str, dict[str, Any]] = {}
    for field in TRACKED_FIELDS:
        new = AccountStatus(item.status) if field == "status" else getattr(item, field)
        old = getattr(account, field)
        if old != new:
            changes[field] = {"old": _str(old), "new": _str(new)}
            setattr(account, field, new)
    return changes


def _str(value: object) -> str | None:
    return None if value is None else str(value)
