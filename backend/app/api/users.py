"""Panel users, invites and the organization. Admins only."""

import uuid

from fastapi import APIRouter, status

from app.api.auth_deps import AdminDep
from app.api.deps import SessionDep
from app.schemas.auth import OrganizationSettingsOut, OrganizationUpdate, UserOut
from app.schemas.users import InviteCreate, InviteCreated, InviteList, InviteOut, ResetLinkOut, UserUpdate
from app.services import organization
from app.services.auth import invites, passwords_flow, users

router = APIRouter()


@router.get("/users", response_model=list[UserOut])
async def list_users(session: SessionDep, _: AdminDep) -> list[UserOut]:
    return [UserOut.model_validate(user) for user in await users.list_users(session)]


@router.patch("/users/{user_id}", response_model=UserOut)
async def update_user(user_id: uuid.UUID, data: UserUpdate, session: SessionDep, admin: AdminDep) -> UserOut:
    return UserOut.model_validate(await users.set_role(session, user_id, data.role, admin=admin))


@router.post("/users/{user_id}/approve", response_model=UserOut)
async def approve_user(user_id: uuid.UUID, session: SessionDep, admin: AdminDep) -> UserOut:
    """Let a sign-up in; nothing is sent, tell them yourself. Reject a sign-up with DELETE /users/{id}."""
    return UserOut.model_validate(await users.approve(session, user_id, admin=admin))


@router.post("/users/{user_id}/reset-link", response_model=ResetLinkOut, status_code=status.HTTP_201_CREATED)
async def create_reset_link(user_id: uuid.UUID, session: SessionDep, admin: AdminDep) -> ResetLinkOut:
    """A one-time password reset link (24 hours) for the admin to pass on; no e-mail is sent."""
    link, expires_at = await passwords_flow.issue_link(session, await users.get(session, user_id), by=admin.email)
    return ResetLinkOut(link=link, expires_at=expires_at)


@router.post("/users/{user_id}/reset-totp", response_model=UserOut)
async def reset_user_totp(user_id: uuid.UUID, session: SessionDep, admin: AdminDep) -> UserOut:
    """Lost phone: 2FA off and the user signed out; the next sign-in sets up a new authenticator."""
    return UserOut.model_validate(await users.reset_totp(session, user_id, admin=admin))


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_user(user_id: uuid.UUID, session: SessionDep, admin: AdminDep) -> None:
    await users.remove(session, user_id, admin=admin)


@router.get("/invites", response_model=InviteList)
async def list_invites(session: SessionDep, _: AdminDep) -> InviteList:
    return InviteList(items=[InviteOut.model_validate(row) for row in await invites.list_open(session)])


@router.post("/invites", response_model=InviteCreated, status_code=status.HTTP_201_CREATED)
async def create_invite(data: InviteCreate, session: SessionDep, admin: AdminDep) -> InviteCreated:
    """A one-time registration link for this e-mail; the admin passes it on (nothing is e-mailed)."""
    row, link = await invites.create(session, email=data.email, role=data.role, admin=admin)
    return InviteCreated(**InviteOut.model_validate(row).model_dump(), link=link)


@router.delete("/invites/{invite_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_invite(invite_id: uuid.UUID, session: SessionDep, _: AdminDep) -> None:
    await invites.revoke(session, invite_id)


@router.get("/organization", response_model=OrganizationSettingsOut)
async def get_organization(session: SessionDep, _: AdminDep) -> OrganizationSettingsOut:
    return OrganizationSettingsOut.model_validate(await organization.get(session))


@router.patch("/organization", response_model=OrganizationSettingsOut)
async def update_organization(data: OrganizationUpdate, session: SessionDep, _: AdminDep) -> OrganizationSettingsOut:
    updated = await organization.update(session, data.model_dump(exclude_none=True))
    return OrganizationSettingsOut.model_validate(updated)
