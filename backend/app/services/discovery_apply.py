"""Store one app discovery result: discovered apps, grants and the directory state of each person.

Merging is idempotent: a scan that reads an overlapping window again only
widens ``first_seen_at`` and ``last_seen_at``. Grants the scan did not see
stay (a person who left still shows the apps they used); their directory
state and token state are refreshed on every scan.
"""

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import select

from app.models import DiscoveredApp, DiscoveredGrant
from app.models.enums import DirectoryStatus, DiscoveredAppStatus

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from app.connectors.discovery import AppGrant, DiscoveryResult
    from app.models import Connection


@dataclass
class ApplyStats:
    apps_found: int = 0
    apps_new: int = 0
    grants_found: int = 0
    new_app_names: list[str] = field(default_factory=list)


@dataclass
class Directory:
    """E-mail (primary or alias) to directory state, the domains of the directory, deletions."""

    statuses: dict[str, DirectoryStatus]
    domains: set[str]
    deleted: dict[str, datetime]

    @classmethod
    def from_result(cls, result: DiscoveryResult) -> Directory:
        statuses: dict[str, DirectoryStatus] = {}
        domains: set[str] = set()
        for user in result.directory:
            status = DirectoryStatus.SUSPENDED if user.status == "suspended" else DirectoryStatus.ACTIVE
            for email in (user.email, *user.aliases):
                statuses[email.lower()] = status
                domains.add(_domain(email))
        return cls(statuses=statuses, domains=domains, deleted={k.lower(): v for k, v in result.deleted_users.items()})

    def classify(self, email: str) -> tuple[DirectoryStatus, datetime | None]:
        email = email.lower()
        if email in self.statuses:
            return self.statuses[email], None
        if email in self.deleted:
            return DirectoryStatus.DELETED, self.deleted[email]
        if _domain(email) in self.domains:
            return DirectoryStatus.DELETED, None  # deleted before the audit window
        return DirectoryStatus.EXTERNAL, None


def app_key(name: str | None, client_id: str) -> str:
    """Grouping key of a discovered app: the lowercased name, or the client id for unnamed clients."""
    cleaned = " ".join((name or "").split()).lower()
    return cleaned[:320] or client_id[:320]


@dataclass
class _AppGroup:
    name: str
    client_ids: set[str] = field(default_factory=set)
    grants: dict[str, list[AppGrant]] = field(default_factory=lambda: defaultdict(list))


def group_grants(grants: list[AppGrant]) -> dict[str, _AppGroup]:
    groups: dict[str, _AppGroup] = {}
    for grant in grants:
        key = app_key(grant.app_name, grant.client_id)
        group = groups.setdefault(key, _AppGroup(name=(grant.app_name or grant.client_id).strip()[:320]))
        group.client_ids.add(grant.client_id)
        group.grants[grant.email.lower()].append(grant)
    return groups


async def apply_discovery(session: AsyncSession, connection: Connection, result: DiscoveryResult) -> ApplyStats:
    now = datetime.now(UTC)
    directory = Directory.from_result(result)
    apps = {
        app.key: app
        for app in await session.scalars(select(DiscoveredApp).where(DiscoveredApp.connection_id == connection.id))
    }
    stats = ApplyStats()
    seen_tokens: set[tuple[str, str]] = set()  # (app key, e-mail) with a live token in this scan
    groups = group_grants(result.grants)

    for key, group in sorted(groups.items()):
        app = apps.get(key)
        if app is None:
            app = DiscoveredApp(
                connection_id=connection.id, key=key, name=group.name, status=DiscoveredAppStatus.NEW, client_ids=[]
            )
            session.add(app)
            apps[key] = app
            stats.apps_new += 1
            stats.new_app_names.append(group.name)
        app.client_ids = sorted(set(app.client_ids or []) | group.client_ids)
        all_grants = [grant for grants in group.grants.values() for grant in grants]
        app.scopes = _union(app.scopes, *(grant.scopes for grant in all_grants))
        app.first_seen_at = _min(app.first_seen_at, *(grant.first_seen_at for grant in all_grants))
        app.last_seen_at = _max(app.last_seen_at, *(grant.last_seen_at for grant in all_grants))
        for email, grants in group.grants.items():
            if any(grant.token_active for grant in grants):
                seen_tokens.add((key, email))
    await session.flush()

    existing = {
        (row.discovered_app_id, row.email): row
        for row in await session.scalars(
            select(DiscoveredGrant).where(DiscoveredGrant.discovered_app_id.in_([app.id for app in apps.values()]))
        )
    }
    for key, group in groups.items():
        app = apps[key]
        for email, grants in group.grants.items():
            row = existing.get((app.id, email))
            if row is None:
                row = DiscoveredGrant(discovered_app_id=app.id, email=email, scopes=[])
                session.add(row)
                existing[(app.id, email)] = row
            row.scopes = _union(row.scopes, *(grant.scopes for grant in grants))
            row.first_seen_at = _min(row.first_seen_at, *(grant.first_seen_at for grant in grants))
            row.last_seen_at = _max(row.last_seen_at, *(grant.last_seen_at for grant in grants))

    keys = {app.id: key for key, app in apps.items()}
    for (app_id, email), row in existing.items():
        row.directory_status, deleted_at = directory.classify(email)
        row.deleted_at = deleted_at or (row.deleted_at if row.directory_status == DirectoryStatus.DELETED else None)
        row.token_active = (keys[app_id], email) in seen_tokens if result.token_inventory else None
        row.updated_at = now
    await session.flush()

    stats.apps_found = len(apps)
    stats.grants_found = len(existing)
    return stats


def _domain(email: str) -> str:
    return email.rpartition("@")[2].lower()


def _union(current: list | None, *more: list[str]) -> list[str]:
    values = list(current or [])
    for scopes in more:
        for scope in scopes:
            if scope not in values:
                values.append(scope)
    return values


def _min(*values: datetime | None) -> datetime | None:
    present = [value for value in values if value is not None]
    return min(present) if present else None


def _max(*values: datetime | None) -> datetime | None:
    present = [value for value in values if value is not None]
    return max(present) if present else None
