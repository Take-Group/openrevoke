"""Pure sync rules: removed accounts and the 30% safety threshold."""

from dataclasses import dataclass
from typing import TYPE_CHECKING

from app.services.matching import normalize_email

if TYPE_CHECKING:
    from app.connectors.base import RemoteAccount

# A sync that would mark more than this share of live accounts as removed fails instead.
REMOVAL_THRESHOLD = 0.30


class RemovalThresholdError(Exception):
    def __init__(self, removed: int, live: int) -> None:
        share = round(100 * removed / live) if live else 0
        super().__init__(
            f"Sync stopped: {removed} of {live} accounts ({share}%) are missing from the app's list, more than "
            f"{round(REMOVAL_THRESHOLD * 100)}%. Nothing was marked as removed. If the removals are real, "
            "run the sync again with force."
        )
        self.removed = removed
        self.live = live


def exceeds_removal_threshold(removed: int, live: int, threshold: float = REMOVAL_THRESHOLD) -> bool:
    return live > 0 and removed / live > threshold


def missing_ids(live_ids: set[str], seen_ids: set[str]) -> set[str]:
    """Live accounts that the full list from the connector no longer has."""
    return live_ids - seen_ids


@dataclass(frozen=True)
class CleanAccount:
    """A remote account normalized to fit the ``account`` columns."""

    external_id: str
    email: str | None
    username: str | None
    display_name: str | None
    role: str | None
    status: str
    raw: dict


def clean_accounts(accounts: list[RemoteAccount]) -> list[CleanAccount]:
    """Normalize e-mails, trim to column sizes, drop duplicate external ids (the first one wins)."""
    seen: set[str] = set()
    result = []
    for account in accounts:
        external_id = account.external_id.strip()[:320]
        if not external_id or external_id in seen:
            continue
        seen.add(external_id)
        result.append(
            CleanAccount(
                external_id=external_id,
                email=_cut(normalize_email(account.email), 320),
                username=_cut(account.username, 320),
                display_name=_cut(account.display_name, 320),
                role=_cut(account.role, 100),
                status=account.status,
                raw=account.raw or {},
            )
        )
    return result


def _cut(value: str | None, size: int) -> str | None:
    if value is None:
        return None
    value = value.strip()
    return value[:size] or None
