"""Loading access profile data in bulk and turning it into drift and response parts.

Shared by ``profiles`` (CRUD), ``profile_members`` (people and drift), ``profile_assignment`` and the
dashboard. Queries take lists of ids, so a page of members costs a few queries, not a few per person.
"""

from collections import defaultdict
from typing import TYPE_CHECKING

from sqlalchemy import and_, or_, select

from app.models import AccessProfile, AccessProfileApp, Account, Action, App, Person, PersonAccessProfile
from app.models.enums import AccountKind, AccountStatus, ActionKind, PersonKind, PersonStatus
from app.schemas.access_profiles import AccessDrift, AccessProfileAppOut, ExtraAccess, MissingAccess, RoleMismatch
from app.schemas.actions import WriteKind
from app.services.access.profile_drift import Drift, Grant, HeldAccount, compute, resolve
from app.services.actions import OPEN_STATUSES
from app.services.costs import Cost, seat_monthly_cost
from app.services.presenters import account_ref, app_logo_url, app_ref, money, price_of

if TYPE_CHECKING:
    import uuid

    from sqlalchemy.ext.asyncio import AsyncSession

    from app.services.conversion import Converter


def seat_price(app: App) -> Cost | None:
    """What one more person costs per month in the app (per-seat apps only)."""
    return seat_monthly_cost(price_of(app), AccountStatus.ACTIVE, AccountKind.PERSON)


def profile_app_out(link: AccessProfileApp, app: App, converter: Converter) -> AccessProfileAppOut:
    price = seat_price(app)
    return AccessProfileAppOut(
        app=app_ref(app),
        logo_url=app_logo_url(app),
        role=link.role,
        seat_price=money(price),
        seat_price_converted=money(converter.convert(price)),
    )


async def profile_apps(
    session: AsyncSession, profile_ids: list[uuid.UUID]
) -> dict[uuid.UUID, list[tuple[AccessProfileApp, App]]]:
    rows = await session.execute(
        select(AccessProfileApp, App)
        .join(App, App.id == AccessProfileApp.app_id)
        .where(AccessProfileApp.profile_id.in_(profile_ids))
        .order_by(App.name)
    )
    result: dict[uuid.UUID, list[tuple[AccessProfileApp, App]]] = defaultdict(list)
    for link, app in rows:
        result[link.profile_id].append((link, app))
    return result


async def profiles_of(session: AsyncSession, person_ids: list[uuid.UUID]) -> dict[uuid.UUID, list[AccessProfile]]:
    rows = await session.execute(
        select(PersonAccessProfile.person_id, AccessProfile)
        .join(AccessProfile, AccessProfile.id == PersonAccessProfile.profile_id)
        .where(PersonAccessProfile.person_id.in_(person_ids))
        .order_by(AccessProfile.name)
    )
    result: dict[uuid.UUID, list[AccessProfile]] = defaultdict(list)
    for person_id, profile in rows:
        result[person_id].append(profile)
    return result


async def grants_of(session: AsyncSession, person_ids: list[uuid.UUID]) -> dict[uuid.UUID, list[Grant]]:
    rows = await session.execute(
        select(PersonAccessProfile.person_id, AccessProfile.id, AccessProfile.name, AccessProfileApp)
        .join(AccessProfile, AccessProfile.id == PersonAccessProfile.profile_id)
        .join(AccessProfileApp, AccessProfileApp.profile_id == AccessProfile.id)
        .where(PersonAccessProfile.person_id.in_(person_ids))
    )
    result: dict[uuid.UUID, list[Grant]] = defaultdict(list)
    for person_id, profile_id, name, link in rows:
        result[person_id].append(Grant(profile_id=profile_id, profile_name=name, app_id=link.app_id, role=link.role))
    return result


async def accounts_of(session: AsyncSession, person_ids: list[uuid.UUID]) -> dict[uuid.UUID, list[tuple[Account, App]]]:
    """Accounts that are not removed, by app name."""
    rows = await session.execute(
        select(Account, App)
        .join(App, App.id == Account.app_id)
        .where(Account.person_id.in_(person_ids), Account.status != AccountStatus.REMOVED)
        .order_by(App.name, Account.id)
    )
    result: dict[uuid.UUID, list[tuple[Account, App]]] = defaultdict(list)
    for account, app in rows:
        result[account.person_id].append((account, app))
    return result


async def creating_of(session: AsyncSession, person_ids: list[uuid.UUID]) -> dict[uuid.UUID, set[uuid.UUID]]:
    """Apps with an open account creation (action or manual task), per person."""
    rows = await session.execute(
        select(Action.person_id, Action.app_id).where(
            Action.person_id.in_(person_ids),
            Action.status.in_(OPEN_STATUSES),
            or_(
                Action.kind == ActionKind.CREATE_ACCOUNT,
                and_(
                    Action.kind == ActionKind.MANUAL_TASK,
                    Action.payload["operation"].astext == WriteKind.CREATE_ACCOUNT,
                ),
            ),
        )
    )
    result: dict[uuid.UUID, set[uuid.UUID]] = defaultdict(set)
    for person_id, app_id in rows:
        result[person_id].add(app_id)
    return result


class DriftData:
    """Drift of several people with the rows needed to present it."""

    def __init__(
        self,
        drifts: dict[uuid.UUID, Drift],
        accounts: dict[uuid.UUID, list[tuple[Account, App]]],
        apps: dict[uuid.UUID, App],
    ) -> None:
        self.drifts = drifts
        self.accounts = {account.id: (account, app) for rows in accounts.values() for account, app in rows}
        self.apps = apps

    def out(self, person_id: uuid.UUID) -> AccessDrift:
        drift = self.drifts.get(person_id, Drift())
        return AccessDrift(
            missing=[
                MissingAccess(
                    app=app_ref(self.apps[grant.app_id]),
                    logo_url=app_logo_url(self.apps[grant.app_id]),
                    role=grant.role,
                    profiles=list(grant.profiles),
                )
                for grant in sorted(drift.missing, key=lambda grant: self.apps[grant.app_id].name.casefold())
            ],
            extra=[
                ExtraAccess(
                    account=account_ref(self.accounts[held.account_id][0]),
                    app=app_ref(self.accounts[held.account_id][1]),
                    role=held.role,
                )
                for held in drift.extra
            ],
            role_mismatch=[
                RoleMismatch(
                    account=account_ref(self.accounts[item.account_id][0]),
                    app=app_ref(self.accounts[item.account_id][1]),
                    role=item.role,
                    expected_role=item.expected_role,
                    profiles=list(item.profiles),
                )
                for item in drift.role_mismatch
            ],
        )


async def drift_of(session: AsyncSession, people: list[Person]) -> DriftData:
    ids = [person.id for person in people]
    grants = await grants_of(session, ids)
    accounts = await accounts_of(session, ids)
    creating = await creating_of(session, ids)
    app_ids = {grant.app_id for items in grants.values() for grant in items}
    apps = {app.id: app for app in await session.scalars(select(App).where(App.id.in_(app_ids)))} if app_ids else {}
    drifts = {
        person.id: compute(
            has_left=person.status == PersonStatus.LEFT,
            grants=resolve(grants.get(person.id, [])),
            accounts=[_held(account) for account, _ in accounts.get(person.id, [])],
            creating=creating.get(person.id, set()),
        )
        for person in people
    }
    return DriftData(drifts, accounts, apps)


async def members_missing_by_profile(
    session: AsyncSession, profile_ids: list[uuid.UUID] | None = None
) -> dict[uuid.UUID, int]:
    """Per profile: active human members who miss at least one app of that profile."""
    query = (
        select(PersonAccessProfile.profile_id, Person)
        .join(Person, Person.id == PersonAccessProfile.person_id)
        .where(Person.status == PersonStatus.ACTIVE, Person.kind == PersonKind.HUMAN)
    )
    if profile_ids is not None:
        query = query.where(PersonAccessProfile.profile_id.in_(profile_ids))
    rows = list(await session.execute(query))
    if not rows:
        return {}
    people = list({person.id: person for _, person in rows}.values())
    data = await drift_of(session, people)
    links = await profile_apps(session, list({profile_id for profile_id, _ in rows}))
    result: dict[uuid.UUID, int] = defaultdict(int)
    for profile_id, person in rows:
        missing = {grant.app_id for grant in data.drifts[person.id].missing}
        if any(link.app_id in missing for link, _ in links.get(profile_id, [])):
            result[profile_id] += 1
    return result


def _held(account: Account) -> HeldAccount:
    return HeldAccount(
        account_id=account.id, app_id=account.app_id, role=account.role, status=account.status, kind=account.kind
    )
