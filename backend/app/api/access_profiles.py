import uuid

from fastapi import APIRouter, Response, status

from app.api.deps import SessionDep
from app.schemas.access_profiles import (
    AccessProfileCreate,
    AccessProfileList,
    AccessProfileMemberList,
    AccessProfileOut,
    AccessProfileUpdate,
    AppRoleSuggestionList,
    MembersAssign,
    MembersAssignResult,
    PersonAccessDrift,
    PersonAccessProfileList,
    ProfileAssign,
    ProfileAssignResult,
    ProfileUnassignResult,
)
from app.services.access import profile_assignment, profile_members, profiles

router = APIRouter()


@router.get("/access-profiles", response_model=AccessProfileList)
async def list_access_profiles(session: SessionDep) -> AccessProfileList:
    """Access profiles by name: apps with roles, member count, monthly seat cost per person."""
    return await profiles.list_profiles(session)


@router.post("/access-profiles", response_model=AccessProfileOut, status_code=status.HTTP_201_CREATED)
async def create_access_profile(data: AccessProfileCreate, session: SessionDep) -> AccessProfileOut:
    """A named set of apps with a role in each ("Developer"). 409 when the name is taken."""
    return await profiles.create_profile(session, data)


@router.get("/access-profiles/app-roles", response_model=AppRoleSuggestionList)
async def list_access_profile_app_roles(session: SessionDep) -> AppRoleSuggestionList:
    """Roles of existing accounts per app, to suggest in the profile form."""
    return await profiles.app_role_suggestions(session)


@router.get("/access-profiles/{profile_id}", response_model=AccessProfileOut)
async def get_access_profile(profile_id: uuid.UUID, session: SessionDep) -> AccessProfileOut:
    return await profiles.get_profile(session, profile_id)


@router.patch("/access-profiles/{profile_id}", response_model=AccessProfileOut)
async def update_access_profile(
    profile_id: uuid.UUID, data: AccessProfileUpdate, session: SessionDep
) -> AccessProfileOut:
    """Only the fields present change; ``apps`` replaces the list. Creates no actions:
    ``members_missing_access`` says how many members now lack an app (assign them again to fix it)."""
    return await profiles.update_profile(session, profile_id, data, data.model_fields_set)


@router.delete("/access-profiles/{profile_id}", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
async def delete_access_profile(profile_id: uuid.UUID, session: SessionDep) -> Response:
    """Removes the profile and its assignments. Accounts in apps stay."""
    await profiles.delete_profile(session, profile_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/access-profiles/{profile_id}/members", response_model=AccessProfileMemberList)
async def list_access_profile_members(profile_id: uuid.UUID, session: SessionDep) -> AccessProfileMemberList:
    """Members with what they miss from their profiles, what they have outside them, and other roles."""
    return await profile_members.list_members(session, profile_id)


@router.post("/access-profiles/{profile_id}/members", response_model=MembersAssignResult)
async def assign_access_profile_members(
    profile_id: uuid.UUID, data: MembersAssign, session: SessionDep
) -> MembersAssignResult:
    """Assigns the profile to people: one onboarding batch per person for the apps they lack.

    Try ``dry_run`` first: it shows the actions and their monthly cost without saving. People who left are skipped.
    """
    return await profile_assignment.assign_members(session, profile_id, data)


@router.get("/people/{person_id}/access-profiles", response_model=PersonAccessProfileList)
async def list_person_access_profiles(person_id: uuid.UUID, session: SessionDep) -> PersonAccessProfileList:
    return await profile_members.person_profiles(session, person_id)


@router.post("/people/{person_id}/access-profiles", response_model=ProfileAssignResult)
async def assign_person_access_profiles(
    person_id: uuid.UUID, data: ProfileAssign, session: SessionDep
) -> ProfileAssignResult:
    """Assigns profiles and creates one onboarding batch (role from the profile) for the apps the person lacks.

    ``dry_run`` previews the actions and their monthly cost without saving. 400 when the person has left.
    """
    return await profile_assignment.assign_to_person(session, person_id, data)


@router.delete("/people/{person_id}/access-profiles/{profile_id}", response_model=ProfileUnassignResult)
async def unassign_person_access_profile(
    person_id: uuid.UUID, profile_id: uuid.UUID, session: SessionDep
) -> ProfileUnassignResult:
    """Removes the profile from the person. Deletes nothing in apps: ``suggested_removals`` lists the accounts
    only this profile gave; create delete_account actions for the ones to remove."""
    return await profile_members.unassign(session, person_id, profile_id)


@router.get("/people/{person_id}/access-drift", response_model=PersonAccessDrift)
async def get_person_access_drift(person_id: uuid.UUID, session: SessionDep) -> PersonAccessDrift:
    """What the person misses from their profiles, what they have outside them, and accounts with another role."""
    return await profile_members.person_drift(session, person_id)
