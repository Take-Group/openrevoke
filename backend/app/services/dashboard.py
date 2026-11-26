"""Dashboard: counts, total monthly cost per currency, alerts."""

from typing import TYPE_CHECKING

from sqlalchemy import func, select

from app.connectors.base import AuthKind
from app.connectors.registry import UnknownConnectorError, get_connector
from app.models.enums import (
    AccountStatus,
    ActionStatus,
    ConnectionStatus,
    PersonKind,
    PersonStatus,
    RequestPolicy,
)
from app.models import AccessProfile, Account, Action, App, Connection, Person, PersonLink
from app.schemas.currencies import ExchangeRatesInfo
from app.schemas.dashboard import Alert, AlertEntityType, AlertKind, AlertSeverity, Dashboard, DashboardCounts
from app.services import exchange_rates
from app.services.access.profile_data import members_missing_by_profile
from app.services.accounts import unassigned_clause
from app.services.apps import SeatStats, seat_stats
from app.services.costs import app_monthly_cost, sum_by_currency
from app.services.discovery import apps_at_risk
from app.services.people_managers import needs_manager_clause
from app.services.people_sources import source_names
from app.services.presenters import money, money_list, price_of

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

ACTIVE_SEAT_STATUSES = (AccountStatus.ACTIVE, AccountStatus.INVITED)
MANAGER_POLICIES = (RequestPolicy.MANAGER, RequestPolicy.MANAGER_THEN_ADMIN)
PROBLEM_STATUSES = (ConnectionStatus.NEEDS_LOGIN, ConnectionStatus.ERROR)


async def get_dashboard(session: AsyncSession) -> Dashboard:
    apps = list(await session.scalars(select(App)))
    stats = await seat_stats(session)
    people = dict(
        (
            await session.execute(
                select(Person.status, func.count()).where(Person.kind == PersonKind.HUMAN).group_by(Person.status)
            )
        ).all()
    )
    actions = dict((await session.execute(select(Action.status, func.count()).group_by(Action.status))).all())
    alerts = [
        *await _left_people_alerts(session),
        *await _failed_action_alerts(session),
        *await _connection_alerts(session),
        *await _unassigned_alerts(session),
        *await _inactive_in_source_alerts(session),
        *await _discovery_alerts(session),
        *await _no_manager_alerts(session, apps),
        *await _profile_access_alerts(session),
    ]
    alerts.sort(key=lambda alert: alert.severity != AlertSeverity.CRITICAL)
    counts = DashboardCounts(
        people_active=people.get(PersonStatus.ACTIVE, 0),
        people_left=people.get(PersonStatus.LEFT, 0),
        apps=len(apps),
        accounts=sum(stat.accounts for stat in stats.values()),
        seats=sum(stat.billable for stat in stats.values()),
        accounts_unassigned=sum(stat.unassigned for stat in stats.values()),
        connections_with_problems=await session.scalar(
            select(func.count()).where(Connection.status.in_(PROBLEM_STATUSES))
        )
        or 0,
        actions_pending_approval=actions.get(ActionStatus.PENDING_APPROVAL, 0),
        actions_failed=actions.get(ActionStatus.FAILED, 0),
    )
    costs = [app_monthly_cost(price_of(app), stats.get(app.id, SeatStats()).billable) for app in apps]
    converter = await exchange_rates.load_converter(session)
    rates = await exchange_rates.latest_info(session)
    return Dashboard(
        counts=counts,
        monthly_cost=money_list(sum_by_currency(costs)),
        monthly_cost_total=money(converter.total(costs)),
        exchange_rates=ExchangeRatesInfo.model_validate(rates) if rates else None,
        alerts=alerts,
    )


async def _left_people_alerts(session: AsyncSession) -> list[Alert]:
    rows = await session.execute(
        select(Account, App, Person)
        .join(App, App.id == Account.app_id)
        .join(Person, Person.id == Account.person_id)
        .where(Person.status == PersonStatus.LEFT, Account.status.in_(ACTIVE_SEAT_STATUSES))
        .order_by(Person.last_name, Person.first_name, App.name)
    )
    return [
        Alert(
            kind=AlertKind.LEFT_PERSON_ACTIVE_ACCOUNT,
            severity=AlertSeverity.CRITICAL,
            message=f"{_name(person)} has left but still has an {account.status} account in {app.name}",
            entity_type=AlertEntityType.ACCOUNT,
            entity_id=account.id,
            app_id=app.id,
            person_id=person.id,
            count=None,
        )
        for account, app, person in rows
    ]


async def _failed_action_alerts(session: AsyncSession) -> list[Alert]:
    rows = await session.execute(
        select(Action, App, Person)
        .join(App, App.id == Action.app_id)
        .outerjoin(Person, Person.id == Action.person_id)
        .where(Action.status == ActionStatus.FAILED)
        .order_by(Action.finished_at.desc())
    )
    alerts = []
    for action, app, person in rows:
        who = f" for {_name(person)}" if person else ""
        error = f": {action.error}" if action.error else ""
        alerts.append(
            Alert(
                kind=AlertKind.ACTION_FAILED,
                severity=AlertSeverity.CRITICAL,
                message=f"{action.kind.replace('_', ' ').capitalize()} in {app.name}{who} failed{error}",
                entity_type=AlertEntityType.ACTION,
                entity_id=action.id,
                app_id=app.id,
                person_id=person.id if person else None,
                count=None,
            )
        )
    return alerts


async def _connection_alerts(session: AsyncSession) -> list[Alert]:
    rows = await session.execute(
        select(Connection, App)
        .join(App, App.id == Connection.app_id)
        .where(Connection.status.in_(PROBLEM_STATUSES))
        .order_by(App.name)
    )
    alerts = []
    for connection, app in rows:
        needs_login = connection.status == ConnectionStatus.NEEDS_LOGIN
        if needs_login and _uses_browser(connection.connector_key):
            message = f"{app.name} needs a new login in the browser"
        elif needs_login:
            message = f"{app.name} rejected the stored credentials. Update them in the connection settings"
        else:
            message = f"{app.name} sync failed" + (f": {connection.last_error}" if connection.last_error else "")
        alerts.append(
            Alert(
                kind=AlertKind.CONNECTION_NEEDS_LOGIN if needs_login else AlertKind.CONNECTION_ERROR,
                severity=AlertSeverity.WARNING,
                message=message,
                entity_type=AlertEntityType.CONNECTION,
                entity_id=connection.id,
                app_id=app.id,
                person_id=None,
                count=None,
            )
        )
    return alerts


async def _unassigned_alerts(session: AsyncSession) -> list[Alert]:
    rows = await session.execute(
        select(App, func.count(Account.id))
        .join(Account, Account.app_id == App.id)
        .where(unassigned_clause())
        .group_by(App.id)
        .order_by(func.count(Account.id).desc(), App.name)
    )
    return [
        Alert(
            kind=AlertKind.UNASSIGNED_ACCOUNTS,
            severity=AlertSeverity.WARNING,
            message=f"{count} account{'s' if count != 1 else ''} in {app.name} without an owner",
            entity_type=AlertEntityType.APP,
            entity_id=app.id,
            app_id=app.id,
            person_id=None,
            count=count,
        )
        for app, count in rows
    ]


async def _inactive_in_source_alerts(session: AsyncSession) -> list[Alert]:
    rows = list(
        await session.execute(
            select(PersonLink, Person)
            .join(Person, Person.id == PersonLink.person_id)
            .where(Person.status == PersonStatus.ACTIVE, PersonLink.is_active.is_(False))
            .order_by(Person.last_name, Person.first_name)
        )
    )
    names = await source_names(session, [link for link, _ in rows])
    return [
        Alert(
            kind=AlertKind.PERSON_INACTIVE_IN_SOURCE,
            severity=AlertSeverity.WARNING,
            message=(
                f"{_name(person)} is inactive in {names.get(link.source_id, 'a source')} but active in Open Revoke"
            ),
            entity_type=AlertEntityType.PERSON,
            entity_id=person.id,
            app_id=None,
            person_id=person.id,
            count=None,
        )
        for link, person in rows
    ]


async def _discovery_alerts(session: AsyncSession) -> list[Alert]:
    """One alert per app found by the scan that people who left, or were removed, signed in to."""
    return [
        Alert(
            kind=AlertKind.DISCOVERED_SIGN_INS_AT_RISK,
            severity=AlertSeverity.WARNING,
            message=(
                f"{_people_who_left(count)} signed in to {app.name}. Check whether they still have an account there"
            ),
            entity_type=AlertEntityType.DISCOVERED_APP,
            entity_id=app.id,
            app_id=app.app_id,
            person_id=None,
            count=count,
        )
        for app, count in await apps_at_risk(session)
    ]


async def _no_manager_alerts(session: AsyncSession, apps: list[App]) -> list[Alert]:
    """Active people without a manager, only while an app sends requests to managers.

    The top of each reporting line (no manager, but people report to them) is not counted.
    """
    if not any(app.request_policy in MANAGER_POLICIES for app in apps):
        return []
    rows = list(
        await session.scalars(
            select(Person.id).where(needs_manager_clause()).order_by(Person.last_name, Person.first_name, Person.id)
        )
    )
    if not rows:
        return []
    count = len(rows)
    return [
        Alert(
            kind=AlertKind.PEOPLE_WITHOUT_MANAGER,
            severity=AlertSeverity.WARNING,
            message=(
                f"{'1 person has' if count == 1 else f'{count} people have'} no manager. "
                "Their access requests go to an admin"
            ),
            entity_type=AlertEntityType.PERSON,
            entity_id=rows[0],
            app_id=None,
            person_id=None,
            count=count,
        )
async def _profile_access_alerts(session: AsyncSession) -> list[Alert]:
    """One alert per access profile whose active members miss one of its apps."""
    counts = await members_missing_by_profile(session)
    if not counts:
        return []
    profiles = await session.scalars(
        select(AccessProfile).where(AccessProfile.id.in_(counts)).order_by(AccessProfile.name)
    )
    return [
        Alert(
            kind=AlertKind.PROFILE_ACCESS_MISSING,
            severity=AlertSeverity.WARNING,
            message=(
                f"{counts[profile.id]} {'person misses' if counts[profile.id] == 1 else 'people miss'} "
                f"access from their profile {profile.name}"
            ),
            entity_type=AlertEntityType.ACCESS_PROFILE,
            entity_id=profile.id,
            app_id=None,
            person_id=None,
            count=counts[profile.id],
        )
        for profile in profiles
    ]


def _people_who_left(count: int) -> str:
    return "1 person who left or was removed" if count == 1 else f"{count} people who left or were removed"


def _uses_browser(connector_key: str) -> bool:
    try:
        return get_connector(connector_key).auth_kind == AuthKind.BROWSER_SESSION
    except UnknownConnectorError:
        return False


def _name(person: Person) -> str:
    return f"{person.first_name} {person.last_name}".strip() or person.primary_email
