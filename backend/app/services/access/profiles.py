"""Access profiles: named sets of apps with a role in each, assigned to people.

This module: CRUD of profiles and ``auto_approving_profile`` (used by access requests). Assigning
profiles to people is in ``profile_assignment``, members and drift in ``profile_members``, the bulk
loaders in ``profile_data``, the drift rules in ``profile_drift``.

Deleting a profile removes its assignments, never accounts. Changing a profile's apps creates no
actions: ``members_missing_access`` in the response says how many members now lack an app, and the
panel offers to assign the profile to them again (``POST /api/access-profiles/{id}/members``).
"""

from collections import Counter
from typing import TYPE_CHECKING

from sqlalchemy import delete, func, select

from app.models import AccessProfile, AccessProfileApp, Account, App, PersonAccessProfile
from app.models.enums import AccountStatus
from app.schemas.access_profiles import (
    AccessProfileAppIn,
    AccessProfileCreate,
    AccessProfileList,
    AccessProfileOut,
    AccessProfileUpdate,
    AppRoleSuggestionList,
    AppRoleSuggestions,
)
from app.services import audit, exchange_rates
from app.services.access.profile_data import members_missing_by_profile, profile_app_out, profile_apps, seat_price
from app.services.costs import sum_by_currency
from app.services.errors import ConflictError, InvalidInputError, NotFoundError
from app.services.presenters import money, money_list

if TYPE_CHECKING:
    import uuid

    from sqlalchemy.ext.asyncio import AsyncSession


async def auto_approving_profile(
    session: AsyncSession, person_id: uuid.UUID, app_id: uuid.UUID
) -> AccessProfile | None:
    """A profile of the person that holds the app and lets its requests skip the manager step.

    First by name when several do. None: the request follows the app's policy.
    """
    return await session.scalar(
        select(AccessProfile)
        .join(PersonAccessProfile, PersonAccessProfile.profile_id == AccessProfile.id)
        .join(AccessProfileApp, AccessProfileApp.profile_id == AccessProfile.id)
        .where(
            PersonAccessProfile.person_id == person_id,
            AccessProfileApp.app_id == app_id,
            AccessProfile.auto_approve_requests.is_(True),
        )
        .order_by(AccessProfile.name)
        .limit(1)
    )


async def get_profile_row(session: AsyncSession, profile_id: uuid.UUID) -> AccessProfile:
    profile = await session.get(AccessProfile, profile_id)
    if profile is None:
        raise NotFoundError("Access profile not found")
    return profile


async def list_profiles(session: AsyncSession) -> AccessProfileList:
    profiles = list(await session.scalars(select(AccessProfile).order_by(func.lower(AccessProfile.name))))
    items = await _outs(session, profiles)
    return AccessProfileList(items=items, total=len(items))


async def get_profile(session: AsyncSession, profile_id: uuid.UUID) -> AccessProfileOut:
    return (await _outs(session, [await get_profile_row(session, profile_id)]))[0]


async def create_profile(session: AsyncSession, data: AccessProfileCreate) -> AccessProfileOut:
    name = _clean_name(data.name)
    await _ensure_name_free(session, name, None)
    profile = AccessProfile(
        name=name, description=_clean(data.description), auto_approve_requests=data.auto_approve_requests
    )
    session.add(profile)
    await session.flush()
    apps = await _set_apps(session, profile, data.apps)
    await audit.record(
        session,
        "access_profile.created",
        "access_profile",
        profile.id,
        {"name": name, "auto_approve_requests": profile.auto_approve_requests, "apps": apps},
    )
    await session.refresh(profile)  # server-side timestamps
    return await get_profile(session, profile.id)


async def update_profile(
    session: AsyncSession, profile_id: uuid.UUID, data: AccessProfileUpdate, fields: set[str]
) -> AccessProfileOut:
    profile = await get_profile_row(session, profile_id)
    changes: dict[str, object] = {}
    if "name" in fields:
        if data.name is None:
            raise InvalidInputError("Name is required")
        name = _clean_name(data.name)
        await _ensure_name_free(session, name, profile.id)
        if name != profile.name:
            changes["name"] = {"from": profile.name, "to": name}
            profile.name = name
    if "description" in fields and _clean(data.description) != profile.description:
        changes["description"] = {"from": profile.description, "to": _clean(data.description)}
        profile.description = _clean(data.description)
    auto_approve = data.auto_approve_requests
    if "auto_approve_requests" in fields and auto_approve is not None and auto_approve != profile.auto_approve_requests:
        changes["auto_approve_requests"] = {"from": profile.auto_approve_requests, "to": auto_approve}
        profile.auto_approve_requests = auto_approve
    if "apps" in fields and data.apps is not None:
        before = await _app_snapshot(session, profile.id)
        after = await _set_apps(session, profile, data.apps)
        if before != after:
            changes["apps"] = {"from": before, "to": after}
    if changes:
        await session.flush()
        await audit.record(session, "access_profile.updated", "access_profile", profile.id, changes)
    await session.refresh(profile)
    return await get_profile(session, profile.id)


async def delete_profile(session: AsyncSession, profile_id: uuid.UUID) -> None:
    """Assignments go with the profile (CASCADE); accounts in apps stay."""
    profile = await get_profile_row(session, profile_id)
    members = await session.scalar(
        select(func.count()).select_from(PersonAccessProfile).where(PersonAccessProfile.profile_id == profile.id)
    )
    await audit.record(
        session, "access_profile.deleted", "access_profile", profile.id, {"name": profile.name, "members": members}
    )
    await session.delete(profile)
    await session.flush()


async def app_role_suggestions(session: AsyncSession) -> AppRoleSuggestionList:
    """Roles seen on accounts per app, for the role field of the profile form."""
    rows = await session.execute(
        select(Account.app_id, Account.role, func.count())
        .where(Account.role.is_not(None), Account.role != "", Account.status != AccountStatus.REMOVED)
        .group_by(Account.app_id, Account.role)
    )
    per_app: dict[uuid.UUID, Counter[str]] = {}
    for app_id, role, count in rows:
        per_app.setdefault(app_id, Counter())[role] += count
    return AppRoleSuggestionList(
        items=[
            AppRoleSuggestions(app_id=app_id, roles=[role for role, _ in counts.most_common()])
            for app_id, counts in per_app.items()
        ]
    )


async def _outs(session: AsyncSession, profiles: list[AccessProfile]) -> list[AccessProfileOut]:
    ids = [profile.id for profile in profiles]
    if not ids:
        return []
    apps = await profile_apps(session, ids)
    members = dict(
        (
            await session.execute(
                select(PersonAccessProfile.profile_id, func.count())
                .where(PersonAccessProfile.profile_id.in_(ids))
                .group_by(PersonAccessProfile.profile_id)
            )
        ).all()
    )
    missing = await members_missing_by_profile(session, ids)
    converter = await exchange_rates.load_converter(session)
    items = []
    for profile in profiles:
        rows = apps.get(profile.id, [])
        costs = [seat_price(app) for _, app in rows]
        items.append(
            AccessProfileOut(
                id=profile.id,
                name=profile.name,
                description=profile.description,
                auto_approve_requests=profile.auto_approve_requests,
                apps=[profile_app_out(link, app, converter) for link, app in rows],
                member_count=members.get(profile.id, 0),
                members_missing_access=missing.get(profile.id, 0),
                cost_per_person=money_list(sum_by_currency(costs)),
                cost_per_person_total=money(converter.total(costs)),
                created_at=profile.created_at,
                updated_at=profile.updated_at,
            )
        )
    return items


async def _set_apps(session: AsyncSession, profile: AccessProfile, apps: list[AccessProfileAppIn]) -> list[dict]:
    """Replaces the profile's apps; a repeated app counts once (the first)."""
    unique: dict[uuid.UUID, str | None] = {}
    for item in apps:
        unique.setdefault(item.app_id, _clean(item.role))
    found = set(await session.scalars(select(App.id).where(App.id.in_(unique)))) if unique else set()
    unknown = [str(app_id) for app_id in unique if app_id not in found]
    if unknown:
        raise InvalidInputError(f"App not found: {', '.join(unknown)}")
    await session.execute(delete(AccessProfileApp).where(AccessProfileApp.profile_id == profile.id))
    session.add_all(
        AccessProfileApp(profile_id=profile.id, app_id=app_id, role=role) for app_id, role in unique.items()
    )
    await session.flush()
    return await _app_snapshot(session, profile.id)


async def _app_snapshot(session: AsyncSession, profile_id: uuid.UUID) -> list[dict]:
    rows = await session.execute(
        select(App.name, AccessProfileApp.role)
        .join(App, App.id == AccessProfileApp.app_id)
        .where(AccessProfileApp.profile_id == profile_id)
        .order_by(App.name)
    )
    return [{"app": name, "role": role} for name, role in rows]


async def _ensure_name_free(session: AsyncSession, name: str, profile_id: uuid.UUID | None) -> None:
    query = select(AccessProfile.id).where(func.lower(AccessProfile.name) == name.lower())
    if profile_id is not None:
        query = query.where(AccessProfile.id != profile_id)
    if await session.scalar(query):
        raise ConflictError(f"A profile named {name!r} already exists")


def _clean_name(value: str) -> str:
    name = value.strip()
    if not name:
        raise InvalidInputError("Name is required")
    return name


def _clean(value: str | None) -> str | None:
    return (value or "").strip() or None
