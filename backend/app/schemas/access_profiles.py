"""Access profiles: apps with a role each, assigned to people; drift between profiles and accounts."""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.actions import ActionOut, OnboardSkipped, WriteMode
from app.schemas.common import AccountRef, ApiModel, AppRef, MoneyAmount, PersonRef


class AccessProfileAppIn(BaseModel):
    app_id: uuid.UUID
    role: str | None = Field(
        default=None, max_length=100, description="Role of the new account in the app, e.g. member; empty: any role"
    )


class AccessProfileCreate(BaseModel):
    """A repeated ``app_id`` counts once (the first one)."""

    name: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=2000)
    auto_approve_requests: bool = Field(
        default=False, description="Access requests for these apps, from people with the profile, skip the manager"
    )
    apps: list[AccessProfileAppIn] = Field(default_factory=list, max_length=200)


class AccessProfileUpdate(BaseModel):
    """Only the fields present change; ``apps`` replaces the whole list."""

    name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=2000)
    auto_approve_requests: bool | None = None
    apps: list[AccessProfileAppIn] | None = Field(default=None, max_length=200)


class AccessProfileAppOut(BaseModel):
    app: AppRef
    logo_url: str | None
    role: str | None
    seat_price: MoneyAmount | None = Field(
        description="What one person adds per month (per-seat apps only), in the app's currency"
    )
    seat_price_converted: MoneyAmount | None = Field(description="seat_price in the organization currency")


class AccessProfileOut(BaseModel):
    id: uuid.UUID
    name: str
    description: str | None
    auto_approve_requests: bool
    apps: list[AccessProfileAppOut] = Field(description="By app name")
    member_count: int
    members_missing_access: int = Field(
        description="Active members who lack an account in an app of this profile (no open creation either)"
    )
    cost_per_person: list[MoneyAmount] = Field(description="Monthly seat prices of the apps, per currency")
    cost_per_person_total: MoneyAmount | None = Field(
        description="cost_per_person in the organization currency; null when a currency has no rate"
    )
    created_at: datetime
    updated_at: datetime


class AccessProfileList(BaseModel):
    items: list[AccessProfileOut]
    total: int


class ProfileRef(ApiModel):
    profile_id: uuid.UUID
    name: str


class AppRoleSuggestions(BaseModel):
    app_id: uuid.UUID
    roles: list[str] = Field(description="Roles of existing accounts in the app, most common first")


class AppRoleSuggestionList(BaseModel):
    items: list[AppRoleSuggestions]


class MissingAccess(BaseModel):
    app: AppRef
    logo_url: str | None
    role: str | None = Field(description="Role the profiles give (null: any)")
    profiles: list[str] = Field(description="Profiles of the person that give the app")


class ExtraAccess(BaseModel):
    account: AccountRef
    app: AppRef
    role: str | None


class RoleMismatch(BaseModel):
    account: AccountRef
    app: AppRef
    role: str = Field(description="Role of the account")
    expected_role: str = Field(description="Role the profiles give")
    profiles: list[str]


class AccessDrift(BaseModel):
    """What a person has against what their profiles give."""

    missing: list[MissingAccess] = Field(description="Apps of the profiles without an account or an open creation")
    extra: list[ExtraAccess] = Field(
        description="Accounts in apps outside every profile of the person; empty when the person has no profile"
    )
    role_mismatch: list[RoleMismatch]


class PersonAccessDrift(AccessDrift):
    person: PersonRef
    profiles: list[ProfileRef]


class PersonAccessProfileOut(BaseModel):
    profile: ProfileRef
    description: str | None
    auto_approve_requests: bool
    apps: list[AccessProfileAppOut]
    assigned_at: datetime
    assigned_by: str | None


class PersonAccessProfileList(BaseModel):
    items: list[PersonAccessProfileOut]


class AccessProfileMember(AccessDrift):
    person: PersonRef
    assigned_at: datetime
    assigned_by: str | None


class AccessProfileMemberList(BaseModel):
    items: list[AccessProfileMember]
    total: int


class ProfileAssign(BaseModel):
    profile_ids: list[uuid.UUID] = Field(min_length=1, max_length=50)
    dry_run: bool = Field(default=False, description="Preview the actions and their cost without saving")


class MembersAssign(BaseModel):
    """Already assigned people stay; they get creations for what they now miss."""

    person_ids: list[uuid.UUID] = Field(min_length=1, max_length=500)
    dry_run: bool = Field(default=False, description="Preview the actions and their cost without saving")


class PlannedAction(BaseModel):
    app: AppRef
    logo_url: str | None
    role: str | None
    write_mode: WriteMode = Field(description="automatic, writes_disabled or manual (a manual task)")
    profiles: list[str]
    monthly_cost: MoneyAmount | None = Field(description="What the new seat adds per month, in the app's currency")
    monthly_cost_converted: MoneyAmount | None


class ProfileAssignResult(BaseModel):
    """With ``dry_run`` nothing is saved: ``planned`` is what saving would create, ``actions`` is empty.

    Otherwise the profiles are assigned and ``actions`` wait for approval as one batch
    (``POST /api/actions/batch/{batch_id}/approve``).
    """

    person: PersonRef
    dry_run: bool
    assigned: list[ProfileRef] = Field(description="Profiles new to the person")
    planned: list[PlannedAction]
    skipped: list[OnboardSkipped] = Field(description="Apps of the profiles the person has, or that are being created")
    warnings: list[str] = Field(description="Two profiles give the same app different roles, and which one wins")
    monthly_cost: list[MoneyAmount] = Field(description="What the new seats add per month, per currency")
    monthly_cost_total: MoneyAmount | None
    batch_id: uuid.UUID | None = Field(description="Batch of the created actions; null for dry_run or no actions")
    actions: list[ActionOut]


class SkippedPerson(BaseModel):
    person: PersonRef
    reason: str


class MembersAssignResult(BaseModel):
    dry_run: bool
    items: list[ProfileAssignResult] = Field(description="One per person, each with its own batch")
    skipped_people: list[SkippedPerson] = Field(description="People who left: they cannot get a profile")
    monthly_cost: list[MoneyAmount]
    monthly_cost_total: MoneyAmount | None


class SuggestedRemoval(BaseModel):
    account: AccountRef
    app: AppRef
    role: str | None
    write_mode: WriteMode = Field(description="What a delete_account action would do in the app")


class ProfileUnassignResult(BaseModel):
    """The profile is removed from the person; nothing is deleted in apps.

    ``suggested_removals``: accounts in apps that only this profile gave. Create ``delete_account``
    actions for the ones to remove (``POST /api/actions``).
    """

    person: PersonRef
    profile: ProfileRef
    suggested_removals: list[SuggestedRemoval]
