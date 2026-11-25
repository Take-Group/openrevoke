"""App discovery, read side: overview, discovered apps with their risks, the apps of one person.

People are matched to sign-ins by e-mail (primary or alias) when read, so a
person added after the scan matches at once. A sign-in is at risk when the
person left (Open Revoke), or is suspended or deleted in the directory.
"""

import uuid
from dataclasses import dataclass
from typing import TYPE_CHECKING

from sqlalchemy import func, select

from app.catalog.lookup import app_catalog
from app.config import settings
from app.connectors.discovery import AppDiscovery
from app.models import Account, App, Connection, DiscoveredApp, DiscoveredGrant, Person, PersonEmail, ScanRun
from app.models.enums import AccountStatus, DirectoryStatus, DiscoveredAppStatus, PersonStatus, ScanRunStatus
from app.schemas.catalog import CatalogMatchOut
from app.schemas.discovery import (
    DiscoveredAppDetail,
    DiscoveredAppOut,
    DiscoveredGrantOut,
    DiscoveryConnector,
    DiscoveryCounts,
    DiscoveryOverview,
    DiscoverySource,
    GrantPerson,
    GrantRisk,
    LinkedApp,
    PersonDiscoveredApp,
    ScanRunOut,
)
from app.services.discovery_scan import is_scan_locked
from app.services.discovery_sources import discovery_connections, discovery_connectors
from app.services.errors import NotFoundError
from app.services.matching import EmailIndex, load_email_index, normalize_email

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


@dataclass(frozen=True)
class PersonInfo:
    id: uuid.UUID
    name: str
    status: PersonStatus


@dataclass
class People:
    index: EmailIndex
    by_id: dict[uuid.UUID, PersonInfo]

    def find(self, email: str) -> PersonInfo | None:
        person_id = self.index.lookup(email).person_id
        return self.by_id.get(person_id) if person_id else None


async def load_people(session: AsyncSession) -> People:
    rows = await session.execute(select(Person.id, Person.first_name, Person.last_name, Person.status))
    by_id = {
        person_id: PersonInfo(person_id, f"{first} {last}".strip(), status) for person_id, first, last, status in rows
    }
    return People(index=await load_email_index(session), by_id=by_id)


def grant_risk(directory_status: DirectoryStatus, person: PersonInfo | None) -> GrantRisk | None:
    if directory_status == DirectoryStatus.DELETED:
        return GrantRisk.DELETED
    if directory_status == DirectoryStatus.SUSPENDED:
        return GrantRisk.SUSPENDED
    if person is not None and person.status == PersonStatus.LEFT:
        return GrantRisk.LEFT
    return None


@dataclass
class AppStats:
    users: int = 0
    at_risk: int = 0
    tokens: int = 0
    tokens_known: bool = False


async def _app_stats(session: AsyncSession, people: People) -> dict[uuid.UUID, AppStats]:
    stats: dict[uuid.UUID, AppStats] = {}
    rows = await session.execute(
        select(
            DiscoveredGrant.discovered_app_id,
            DiscoveredGrant.email,
            DiscoveredGrant.directory_status,
            DiscoveredGrant.token_active,
        )
    )
    for app_id, email, directory_status, token_active in rows:
        stat = stats.setdefault(app_id, AppStats())
        stat.users += 1
        if grant_risk(directory_status, people.find(email)) is not None:
            stat.at_risk += 1
        if token_active is not None:
            stat.tokens_known = True
            stat.tokens += int(token_active)
    return stats


async def _linked_apps(session: AsyncSession, app_ids: set[uuid.UUID]) -> dict[uuid.UUID, LinkedApp]:
    if not app_ids:
        return {}
    rows = await session.execute(select(App.id, App.name).where(App.id.in_(app_ids)))
    return {app_id: LinkedApp(id=app_id, name=name) for app_id, name in rows}


def catalog_match(app: DiscoveredApp) -> CatalogMatchOut | None:
    return CatalogMatchOut.of(app_catalog().match(app.name, list(app.client_ids or [])))


def _app_out(app: DiscoveredApp, stat: AppStats, linked: dict[uuid.UUID, LinkedApp]) -> DiscoveredAppOut:
    return DiscoveredAppOut(
        id=app.id,
        name=app.name,
        catalog=catalog_match(app),
        status=app.status,
        app=linked.get(app.app_id) if app.app_id else None,
        client_ids=list(app.client_ids or []),
        scopes=list(app.scopes or []),
        first_seen_at=app.first_seen_at,
        last_seen_at=app.last_seen_at,
        users=stat.users,
        users_at_risk=stat.at_risk,
        active_tokens=stat.tokens if stat.tokens_known else None,
    )


async def apps_at_risk(session: AsyncSession) -> list[tuple[DiscoveredApp, int]]:
    """Not ignored apps with sign-ins of people who left or were removed, most at-risk people first."""
    stats = await _app_stats(session, await load_people(session))
    apps = await session.scalars(select(DiscoveredApp).where(DiscoveredApp.status != DiscoveredAppStatus.IGNORED))
    found = [(app, stats[app.id].at_risk) for app in apps if app.id in stats and stats[app.id].at_risk]
    return sorted(found, key=lambda item: (-item[1], item[0].name.lower()))


async def list_discovered_apps(
    session: AsyncSession,
    *,
    q: str | None,
    status: DiscoveredAppStatus | None,
    at_risk: bool,
    limit: int,
    offset: int,
) -> tuple[list[DiscoveredAppOut], int]:
    """Apps with at-risk sign-ins first, then by number of people. Filtered and paged in memory."""
    query = select(DiscoveredApp)
    if q:
        query = query.where(DiscoveredApp.name.ilike(f"%{q.strip()}%"))
    if status:
        query = query.where(DiscoveredApp.status == status)
    apps = list(await session.scalars(query))
    stats = await _app_stats(session, await load_people(session))
    if at_risk:
        apps = [app for app in apps if stats.get(app.id, AppStats()).at_risk > 0]

    def order(app: DiscoveredApp) -> tuple[int, int, str]:
        stat = stats.get(app.id, AppStats())
        return -stat.at_risk, -stat.users, app.name.lower()

    apps.sort(key=order)
    page = apps[offset : offset + limit]
    linked = await _linked_apps(session, {app.app_id for app in page if app.app_id})
    return [_app_out(app, stats.get(app.id, AppStats()), linked) for app in page], len(apps)


async def get_discovered_app(session: AsyncSession, discovered_app_id: uuid.UUID) -> DiscoveredAppDetail:
    app = await session.get(DiscoveredApp, discovered_app_id)
    if app is None:
        raise NotFoundError("Discovered app not found")
    people = await load_people(session)
    grants = list(
        await session.scalars(select(DiscoveredGrant).where(DiscoveredGrant.discovered_app_id == discovered_app_id))
    )
    items = []
    stat = AppStats()
    for grant in grants:
        person = people.find(grant.email)
        risk = grant_risk(grant.directory_status, person)
        stat.users += 1
        stat.at_risk += int(risk is not None)
        if grant.token_active is not None:
            stat.tokens_known = True
            stat.tokens += int(grant.token_active)
        items.append(
            DiscoveredGrantOut(
                id=grant.id,
                email=grant.email,
                person=GrantPerson(id=person.id, name=person.name, status=person.status) if person else None,
                directory_status=grant.directory_status,
                deleted_at=grant.deleted_at,
                first_seen_at=grant.first_seen_at,
                last_seen_at=grant.last_seen_at,
                token_active=grant.token_active,
                scopes=list(grant.scopes or []),
                risk=risk,
            )
        )
    items.sort(key=lambda item: (item.risk is None, -(item.last_seen_at.timestamp() if item.last_seen_at else 0)))
    linked = await _linked_apps(session, {app.app_id} if app.app_id else set())
    return DiscoveredAppDetail(**_app_out(app, stat, linked).model_dump(), grants=items)


async def person_discovered_apps(session: AsyncSession, person_id: uuid.UUID) -> list[PersonDiscoveredApp]:
    person = await session.get(Person, person_id)
    if person is None:
        raise NotFoundError("Person not found")
    emails = {person.primary_email}
    emails |= set(await session.scalars(select(PersonEmail.email).where(PersonEmail.person_id == person_id)))
    rows = list(
        await session.execute(
            select(DiscoveredGrant, DiscoveredApp)
            .join(DiscoveredApp, DiscoveredApp.id == DiscoveredGrant.discovered_app_id)
            .where(DiscoveredGrant.email.in_({normalize_email(email) for email in emails}))
        )
    )
    linked = await _linked_apps(session, {app.app_id for _, app in rows if app.app_id})
    with_account = set(
        await session.scalars(
            select(Account.app_id).where(Account.person_id == person_id, Account.status != AccountStatus.REMOVED)
        )
    )
    items = [
        PersonDiscoveredApp(
            discovered_app_id=app.id,
            name=app.name,
            catalog=catalog_match(app),
            status=app.status,
            app=linked.get(app.app_id) if app.app_id else None,
            email=grant.email,
            directory_status=grant.directory_status,
            first_seen_at=grant.first_seen_at,
            last_seen_at=grant.last_seen_at,
            token_active=grant.token_active,
            has_account=app.app_id in with_account if app.app_id else False,
        )
        for grant, app in rows
        if app.status != DiscoveredAppStatus.IGNORED
    ]
    items.sort(key=lambda item: (-(item.last_seen_at.timestamp() if item.last_seen_at else 0), item.name.lower()))
    return items


async def overview(session: AsyncSession) -> DiscoveryOverview:
    connections = await discovery_connections(session)
    source = await _source(session, connections[0]) if connections else None
    connection_ids = [connection.id for connection in connections]
    last_scan = await _last_scan(session, connection_ids, ok_only=False)
    last_ok = await _last_scan(session, connection_ids, ok_only=True)
    running = bool(last_scan and last_scan.status == ScanRunStatus.RUNNING) or any(
        [await is_scan_locked(connection_id) for connection_id in connection_ids]
    )
    return DiscoveryOverview(
        source=source,
        connectors=[
            DiscoveryConnector(
                key=connector.key,
                display_name=connector.display_name,
                required_scopes=list(connector.discovery_scopes),
                optional_scopes=list(connector.optional_discovery_scopes),
            )
            for connector in discovery_connectors()
            if isinstance(connector, AppDiscovery)
        ],
        last_scan=ScanRunOut.model_validate(last_scan) if last_scan else None,
        last_successful_scan=ScanRunOut.model_validate(last_ok) if last_ok else None,
        scan_running=running,
        counts=await _counts(session),
        google_oauth_redirect_uri=settings.google_oauth_redirect_uri,
    )


async def _source(session: AsyncSession, connection: Connection) -> DiscoverySource:
    app = await session.get(App, connection.app_id)
    return DiscoverySource(
        connection_id=connection.id,
        app_id=connection.app_id,
        app_name=app.name if app else "",
        connector_key=connection.connector_key,
        connection_status=connection.status,
        last_synced_at=connection.last_synced_at,
    )


async def _last_scan(session: AsyncSession, connection_ids: list[uuid.UUID], *, ok_only: bool) -> ScanRun | None:
    if not connection_ids:
        return None
    query = select(ScanRun).where(ScanRun.connection_id.in_(connection_ids))
    if ok_only:
        query = query.where(ScanRun.status == ScanRunStatus.OK)
    return await session.scalar(query.order_by(ScanRun.started_at.desc()).limit(1))


async def _counts(session: AsyncSession) -> DiscoveryCounts:
    by_status = dict(
        (await session.execute(select(DiscoveredApp.status, func.count()).group_by(DiscoveredApp.status))).all()
    )
    people = await load_people(session)
    stats = await _app_stats(session, people)
    ignored = set(
        await session.scalars(select(DiscoveredApp.id).where(DiscoveredApp.status == DiscoveredAppStatus.IGNORED))
    )
    visible = {app_id: stat for app_id, stat in stats.items() if app_id not in ignored}
    emails = set(
        await session.scalars(
            select(DiscoveredGrant.email).where(DiscoveredGrant.discovered_app_id.notin_(ignored or {uuid.UUID(int=0)}))
        )
    )
    return DiscoveryCounts(
        apps=sum(by_status.values()),
        apps_new=by_status.get(DiscoveredAppStatus.NEW, 0),
        apps_tracked=by_status.get(DiscoveredAppStatus.TRACKED, 0),
        apps_ignored=by_status.get(DiscoveredAppStatus.IGNORED, 0),
        people=len(emails),
        grants_at_risk=sum(stat.at_risk for stat in visible.values()),
        apps_at_risk=sum(1 for stat in visible.values() if stat.at_risk),
    )
