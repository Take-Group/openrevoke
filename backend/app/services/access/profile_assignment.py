"""Assigning access profiles to people: the assignment plus one onboarding batch for what they lack.

- Every app of the chosen profiles goes to ``onboarding`` with the role the profiles give (the first
  profile by name that sets one; a different role in another profile is a warning).
- Apps the person has, or that are being created, are skipped by onboarding as usual.
- ``dry_run`` saves nothing and returns the planned actions and what the new seats cost per month,
  in the app currency and in the organization currency.
- A person who has left cannot get a profile (400 for one person; skipped in a bulk assignment).
- Profiles already assigned stay as they were; the person still gets creations for what they miss,
  which is how "Create actions for N people" works after a profile gains an app.
"""

from typing import TYPE_CHECKING

from sqlalchemy import select

from app.models import AccessProfile, AccessProfileApp, Person, PersonAccessProfile
from app.models.enums import PersonStatus
from app.schemas.access_profiles import (
    MembersAssign,
    MembersAssignResult,
    PlannedAction,
    ProfileAssign,
    ProfileAssignResult,
    ProfileRef,
    SkippedPerson,
)
from app.schemas.actions import OnboardApp, OnboardRequest, OnboardSkipped
from app.services import audit, exchange_rates, onboarding
from app.services.access.profile_data import grants_of, seat_price
from app.services.access.profile_drift import Grant, resolve
from app.services.access.profiles import get_profile_row
from app.services.auth.actor import current_actor
from app.services.costs import Cost, sum_by_currency
from app.services.errors import InvalidInputError, NotFoundError
from app.services.presenters import app_logo_url, app_ref, money, money_list, person_ref

if TYPE_CHECKING:
    import uuid

    from sqlalchemy.ext.asyncio import AsyncSession

    from app.services.conversion import Converter


async def assign_to_person(session: AsyncSession, person_id: uuid.UUID, data: ProfileAssign) -> ProfileAssignResult:
    person = await onboarding.onboardable_person(session, person_id)
    profiles = await _profiles(session, data.profile_ids)
    converter = await exchange_rates.load_converter(session)
    return await _assign(session, person, profiles, dry_run=data.dry_run, converter=converter)


async def assign_members(session: AsyncSession, profile_id: uuid.UUID, data: MembersAssign) -> MembersAssignResult:
    """One batch per person. People who left are skipped and listed."""
    profile = await get_profile_row(session, profile_id)
    people = {
        person.id: person for person in await session.scalars(select(Person).where(Person.id.in_(data.person_ids)))
    }
    unknown = [str(person_id) for person_id in data.person_ids if person_id not in people]
    if unknown:
        raise InvalidInputError(f"Person not found: {', '.join(unknown)}")
    converter = await exchange_rates.load_converter(session)
    items: list[ProfileAssignResult] = []
    skipped: list[SkippedPerson] = []
    for person_id in dict.fromkeys(data.person_ids):
        person = people[person_id]
        if person.status == PersonStatus.LEFT:
            skipped.append(SkippedPerson(person=person_ref(person), reason="The person has left"))
            continue
        items.append(await _assign(session, person, [profile], dry_run=data.dry_run, converter=converter))
    costs = [_cost(item) for result in items for item in result.planned]
    return MembersAssignResult(
        dry_run=data.dry_run,
        items=items,
        skipped_people=skipped,
        monthly_cost=money_list(sum_by_currency(costs)),
        monthly_cost_total=money(converter.total(costs)),
    )


async def _assign(
    session: AsyncSession,
    person: Person,
    profiles: list[AccessProfile],
    *,
    dry_run: bool,
    converter: Converter,
) -> ProfileAssignResult:
    assigned = set(
        await session.scalars(select(PersonAccessProfile.profile_id).where(PersonAccessProfile.person_id == person.id))
    )
    new_profiles = [profile for profile in profiles if profile.id not in assigned]

    chosen_grants = await _grants(session, profiles)
    chosen_keys = {(grant.profile_id, grant.app_id) for grant in chosen_grants}
    existing = (await grants_of(session, [person.id])).get(person.id, [])
    others = [grant for grant in existing if (grant.profile_id, grant.app_id) not in chosen_keys]
    grants = resolve([*others, *chosen_grants])
    chosen_apps = [grants.by_app[app_id] for app_id in dict.fromkeys(grant.app_id for grant in chosen_grants)]
    planned = await onboarding.plan(
        session, person, [OnboardApp(app_id=grant.app_id, role=grant.role) for grant in chosen_apps]
    )
    profiles_by_app = {grant.app_id: list(grant.profiles) for grant in chosen_apps}
    planned_out = [
        PlannedAction(
            app=app_ref(item.app),
            logo_url=app_logo_url(item.app),
            role=item.role,
            write_mode=item.write_mode,
            profiles=profiles_by_app.get(item.app.id, []),
            monthly_cost=money(seat_price(item.app)),
            monthly_cost_converted=money(converter.convert(seat_price(item.app))),
        )
        for item in planned
        if item.skip is None
    ]
    skipped = [OnboardSkipped(app=app_ref(item.app), reason=item.skip) for item in planned if item.skip is not None]
    warnings = [
        f"{conflict.chosen_profile} and {conflict.other_profile} give different roles in "
        f"{_app_name(planned, conflict.app_id)}: {conflict.chosen_role} (from {conflict.chosen_profile}) is used"
        for conflict in grants.conflicts
        if conflict.app_id in profiles_by_app
    ]
    costs = [seat_price(item.app) for item in planned if item.skip is None]

    batch_id = None
    actions = []
    if not dry_run:
        await _save_assignments(session, person, new_profiles)
        if planned_out:
            result = await onboarding.onboard_person(
                session,
                person.id,
                OnboardRequest(apps=[OnboardApp(app_id=item.app.app_id, role=item.role) for item in planned_out]),
                audit_note={"access_profiles": [profile.name for profile in profiles]},
            )
            batch_id = result.batch_id
            actions = result.actions
    return ProfileAssignResult(
        person=person_ref(person),
        dry_run=dry_run,
        assigned=[ProfileRef(profile_id=profile.id, name=profile.name) for profile in new_profiles],
        planned=planned_out,
        skipped=skipped,
        warnings=warnings,
        monthly_cost=money_list(sum_by_currency(costs)),
        monthly_cost_total=money(converter.total(costs)),
        batch_id=batch_id,
        actions=actions,
    )


async def _save_assignments(session: AsyncSession, person: Person, profiles: list[AccessProfile]) -> None:
    actor = current_actor.get()
    for profile in profiles:
        session.add(PersonAccessProfile(person_id=person.id, profile_id=profile.id, assigned_by=actor))
        await session.flush()
        await audit.record(
            session,
            "access_profile.assigned",
            "access_profile",
            profile.id,
            {"profile": profile.name, "person": person.primary_email},
            person_id=person.id,
        )


async def _profiles(session: AsyncSession, profile_ids: list[uuid.UUID]) -> list[AccessProfile]:
    found = {
        profile.id: profile
        for profile in await session.scalars(select(AccessProfile).where(AccessProfile.id.in_(profile_ids)))
    }
    unknown = [str(profile_id) for profile_id in profile_ids if profile_id not in found]
    if unknown:
        raise NotFoundError(f"Access profile not found: {', '.join(unknown)}")
    return sorted(found.values(), key=lambda profile: profile.name.casefold())


async def _grants(session: AsyncSession, profiles: list[AccessProfile]) -> list[Grant]:
    if not profiles:
        return []
    names = {profile.id: profile.name for profile in profiles}
    links = await session.scalars(select(AccessProfileApp).where(AccessProfileApp.profile_id.in_(names)))
    return [
        Grant(profile_id=link.profile_id, profile_name=names[link.profile_id], app_id=link.app_id, role=link.role)
        for link in links
    ]


def _app_name(planned: list[onboarding.PlannedApp], app_id: uuid.UUID) -> str:
    return next((item.app.name for item in planned if item.app.id == app_id), "an app")


def _cost(item: PlannedAction) -> Cost | None:
    return Cost(item.monthly_cost.currency, item.monthly_cost.amount) if item.monthly_cost else None
