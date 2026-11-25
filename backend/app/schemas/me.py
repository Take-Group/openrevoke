"""``/api/me``: what a signed-in user sees about themselves (role ``user`` sees only this)."""

import uuid
from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field

from app.models.enums import AccountStatus
from app.schemas.common import ApiModel, AppRef, PersonRef


class RequestState(StrEnum):
    WAITING_FOR_APPROVAL = "waiting_for_approval"
    IN_PROGRESS = "in_progress"  # approved: the account is being created, by the connector or an admin
    DONE = "done"
    FAILED = "failed"
    CANCELLED = "cancelled"  # an admin rejected or cancelled it


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
    state: RequestState
    message: str | None
    created_at: datetime


class RequestableApp(ApiModel):
    app: AppRef
    needs_approval: bool = Field(description="False: the account is created without waiting for an admin")


class MyAccess(BaseModel):
    person: PersonRef | None = Field(
        description="The person with the user's e-mail (primary or alias); null when the company does not list them"
    )
    accounts: list[MyAccount]
    requests: list[MyRequest] = Field(description="Newest first, at most 50")
    requestable_apps: list[RequestableApp] = Field(
        description="Apps the user can ask for: self-service on, no account and no open request yet"
    )


class MyAccessRequestCreate(BaseModel):
    app_id: uuid.UUID
    message: str | None = Field(default=None, max_length=2000, description="Why the user needs it, for the admin")


class MyAccessRequestResult(BaseModel):
    outcome: str = Field(
        description="in_progress, waiting_for_approval, waiting_for_admin, already_has_account, already_requested "
        "or not_available"
    )
    app_name: str
    note: str | None
