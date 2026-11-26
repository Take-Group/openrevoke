"""``/api/me``: what a signed-in user sees about themselves and their reports (role ``user`` sees only this)."""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.models.enums import AccessRequestStatus, AccountStatus, RequestFallbackReason, RequestPolicy
from app.schemas.access_requests import WaitingFor
from app.schemas.common import ApiModel, AppRef, PersonRef


class MyAccount(ApiModel):
    account_id: uuid.UUID
    app: AppRef
    email: str | None
    username: str | None
    role: str | None = Field(description="Role in the app, as the app reports it")
    status: AccountStatus
    first_seen_at: datetime
    last_seen_at: datetime | None


class MyRequest(ApiModel):
    request_id: uuid.UUID
    app: AppRef
    status: AccessRequestStatus
    waiting_for: WaitingFor | None = Field(description="Who decides next: the manager or an admin")
    approver: PersonRef | None = Field(description="The manager the request waits for (or waited for)")
    fallback_reason: RequestFallbackReason | None = Field(description="Why an admin decides instead of the manager")
    justification: str | None
    role: str | None
    rejection_comment: str | None = Field(description="Why it was rejected, when it was")
    requested_by: str | None
    on_behalf: bool = Field(description="The manager asked for the person")
    created_at: datetime
    closed_at: datetime | None


class RequestableApp(ApiModel):
    app: AppRef
    policy: RequestPolicy = Field(description="Who approves: automatic, manager, manager_then_admin or admin")
    roles: list[str] = Field(description="Roles of existing accounts in the app, as suggestions")


class MyAccess(BaseModel):
    person: PersonRef | None = Field(
        description="The person with the user's e-mail (primary or alias); null when the company does not list them"
    )
    accounts: list[MyAccount]
    requests: list[MyRequest] = Field(description="Newest first, at most 50")
    requestable_apps: list[RequestableApp] = Field(
        description="Apps the user can ask for: policy not off, no account and no open request yet"
    )


class MyAccessRequestCreate(BaseModel):
    app_id: uuid.UUID
    justification: str = Field(min_length=1, max_length=2000, description="Why it is needed; the approver reads it")
    role: str | None = Field(default=None, max_length=100, description="Role asked for in the app")
    person_id: uuid.UUID | None = Field(
        default=None, description="Ask for one of your reports (you are their manager); empty asks for yourself"
    )


class MyAccessRequestResult(BaseModel):
    outcome: str = Field(
        description="in_progress, waiting_for_manager, waiting_for_approval (an admin), waiting_for_admin (an admin "
        "creates it by hand), already_has_account or not_available"
    )
    app_name: str
    note: str | None = Field(description="waiting_for_manager: the manager's name; else why it waits for an admin")
    request_id: uuid.UUID | None


class TeamMember(BaseModel):
    person: PersonRef
    apps: list[AppRef] = Field(description="Apps where the person has an account")
    requestable_apps: list[RequestableApp]


class MyTeam(BaseModel):
    reports: list[TeamMember] = Field(description="People whose manager is the signed-in user, by name")
