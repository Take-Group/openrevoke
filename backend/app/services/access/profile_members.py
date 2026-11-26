"""People and their access profiles: a person's profiles and drift, a profile's members, unassigning.

Unassigning never removes accounts: it returns the accounts that only this profile gave the person
(``suggested_removals``) and the panel lets an admin create ``delete_account`` actions for them.
"""

from typing import TYPE_CHECKING

from sqlalchemy import delete, select

from app.models import AccessProfileApp, Account, Action, App, Connection, Person, PersonAccessProfile
from app.models.enums import AccountKind, AccountStatus, ActionKind
from app.schemas.access_profiles import (
    AccessProfileMember,
    AccessProfileMemberList,
    PersonAccessDrift,
    PersonAccessProfileList,
    PersonAccessProfileOut,
    ProfileRef,
    ProfileUnassignResult,
    SuggestedRemoval,
)
from app.schemas.actions import WriteKind
from app.services import audit, exchange_rates
from app.services.access.profile_data import drift_of, grants_of, profile_app_out, profile_apps, profiles_of
from app.services.access.profiles import get_profile_row
from app.services.actions import OPEN_STATUSES
from app.services.capabilities import write_mode
from app.services.errors import NotFoundError
from app.services.presenters import account_ref, app_ref, person_ref

if TYPE_CHECKING:
    import uuid

    from sqlalchemy.ext.asyncio import AsyncSession

REMOVING_KINDS = (ActionKind.DELETE_ACCOUNT, ActionKind.MANUAL_TASK)


async def _person(session: AsyncSession, person_id: uuid.UUID) -> Person:
    person = await session.get(Person, person_id)
    if person is None:
        raise NotFoundError("Person not found")
    return person


async def person_profiles(session: AsyncSession, person_id: uuid.UUID) -> PersonAccessProfileList:
    await _person(session, person_id)
    rows = list(
        await session.execute(
            select(PersonAccessProfile)
            .where(PersonAccessProfile.person_id == person_id)
            .order_by(PersonAccessProfile.assigned_at)
        )
    )
    profiles = {profile.id: profile for profile in (await profiles_of(session, [person_id])).get(person_id, [])}
    apps = await profile_apps(session, list(profiles))
    converter = await exchange_rates.load_converter(session)
    items = []
    for (link,) in rows:
        profile = profiles[link.profile_id]
        items.append(
            PersonAccessProfileOut(
                profile=ProfileRef(profile_id=profile.id, name=profile.name),
                description=profile.description,
                auto_approve_requests=profile.auto_approve_requests,
                apps=[profile_app_out(app_link, app, converter) for app_link, app in apps.get(profile.id, [])],
                assigned_at=link.assigned_at,
                assigned_by=link.assigned_by,
            )
        )
    items.sort(key=lambda item: item.profile.name.casefold())
    return PersonAccessProfileList(items=items)


async def person_drift(session: AsyncSession, person_id: uuid.UUID) -> PersonAccessDrift:
    person = await _person(session, person_id)
    data = await drift_of(session, [person])
    profiles = (await profiles_of(session, [person.id])).get(person.id, [])
    return PersonAccessDrift(
        person=person_ref(person),
        profiles=[ProfileRef(profile_id=profile.id, name=profile.name) for profile in profiles],
        **data.out(person.id).model_dump(),
    )


async def list_members(session: AsyncSession, profile_id: uuid.UUID) -> AccessProfileMemberList:
    """Members by name, each with their drift against all their profiles."""
    await get_profile_row(session, profile_id)
    rows = list(
        await session.execute(
            select(PersonAccessProfile, Person)
            .join(Person, Person.id == PersonAccessProfile.person_id)
            .where(PersonAccessProfile.profile_id == profile_id)
            .order_by(Person.last_name, Person.first_name, Person.primary_email)
        )
    )
    data = await drift_of(session, [person for _, person in rows])
    items = [
        AccessProfileMember(
            person=person_ref(person),
            assigned_at=link.assigned_at,
            assigned_by=link.assigned_by,
            **data.out(person.id).model_dump(),
        )
        for link, person in rows
    ]
    return AccessProfileMemberList(items=items, total=len(items))


async def unassign(session: AsyncSession, person_id: uuid.UUID, profile_id: uuid.UUID) -> ProfileUnassignResult:
    person = await _person(session, person_id)
    profile = await get_profile_row(session, profile_id)
    result = await session.execute(
        delete(PersonAccessProfile).where(
            PersonAccessProfile.person_id == person.id, PersonAccessProfile.profile_id == profile.id
        )
    )
    if not result.rowcount:
        raise NotFoundError("The person does not have this profile")
    await session.flush()
    await audit.record(
        session,
        "access_profile.unassigned",
        "access_profile",
        profile.id,
        {"profile": profile.name, "person": person.primary_email},
        person_id=person.id,
    )
    return ProfileUnassignResult(
        person=person_ref(person),
        profile=ProfileRef(profile_id=profile.id, name=profile.name),
        suggested_removals=await _suggested_removals(session, person, profile.id),
    )


async def _suggested_removals(session: AsyncSession, person: Person, profile_id: uuid.UUID) -> list[SuggestedRemoval]:
    """Accounts in apps of the removed profile that no other profile of the person gives.

    Service accounts and accounts with an open removal are left out.
    """
    profile_app_ids = set(
        await session.scalars(select(AccessProfileApp.app_id).where(AccessProfileApp.profile_id == profile_id))
    )
    still_given = {grant.app_id for grant in (await grants_of(session, [person.id])).get(person.id, [])}
    app_ids = profile_app_ids - still_given
    if not app_ids:
        return []
    rows = list(
        await session.execute(
            select(Account, App, Connection)
            .join(App, App.id == Account.app_id)
            .outerjoin(Connection, Connection.app_id == App.id)
            .where(
                Account.person_id == person.id,
                Account.app_id.in_(app_ids),
                Account.status != AccountStatus.REMOVED,
                Account.kind != AccountKind.SERVICE,
            )
            .order_by(App.name, Account.id)
        )
    )
    busy = set(
        await session.scalars(
            select(Action.account_id).where(
                Action.account_id.in_([account.id for account, _, _ in rows]),
                Action.status.in_(OPEN_STATUSES),
                Action.kind.in_(REMOVING_KINDS),
            )
        )
    )
    return [
        SuggestedRemoval(
            account=account_ref(account),
            app=app_ref(app),
            role=account.role,
            write_mode=write_mode(connection, WriteKind.DELETE_ACCOUNT),
        )
        for account, app, connection in rows
        if account.id not in busy
    ]
