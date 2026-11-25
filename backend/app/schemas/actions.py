import uuid
from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field

from app.models.enums import ActionKind, ActionReason, ActionStatus
from app.schemas.common import AccountRef, ApiModel, AppRef, PersonRef
from app.schemas.recipe_fixes import RecipeFixOut


class WriteKind(StrEnum):
    CREATE_ACCOUNT = "create_account"
    DELETE_ACCOUNT = "delete_account"


class WriteMode(StrEnum):
    """What happens with a write to an app, shown before the action is created."""

    AUTOMATIC = "automatic"  # the connector writes after approval
    WRITES_DISABLED = "writes_disabled"  # the connector can, but approval fails until "Allow writes" is on
    MANUAL = "manual"  # a manual task for a person


class ActionPayload(BaseModel):
    """What the action sends to the app, shown before approval."""

    operation: WriteKind | None = Field(
        default=None, description="For manual_task: what the person has to do by hand in the app"
    )
    email: str | None = None
    role: str | None = None


class ActionCreate(BaseModel):
    """A new write. Apps whose connector cannot do it get a manual_task instead.

    ``delete_account`` needs ``account_id``. ``create_account`` needs
    ``person_id``; ``email`` defaults to the person's primary e-mail.
    """

    kind: WriteKind
    app_id: uuid.UUID
    person_id: uuid.UUID | None = None
    account_id: uuid.UUID | None = None
    email: str | None = Field(default=None, max_length=320)
    role: str | None = Field(default=None, max_length=100)


class ActionOut(ApiModel):
    id: uuid.UUID
    kind: ActionKind
    status: ActionStatus
    reason: ActionReason
    batch_id: uuid.UUID | None
    person: PersonRef | None
    app: AppRef
    account: AccountRef | None
    payload: ActionPayload
    approved_at: datetime | None
    started_at: datetime | None
    finished_at: datetime | None
    result: dict[str, Any] | None = Field(
        description="What the write and its verification returned (remote account, attempts). Never a secret"
    )
    error: str | None
    has_secret_result: bool = Field(
        description="A one-time secret (temporary password) waits for POST /api/actions/{id}/reveal-secret"
    )
    suspends: bool = Field(description='delete_account suspends instead of deleting (Google Workspace): "Suspend"')
    has_screenshot: bool = Field(
        default=False, description="A click recipe stopped: GET /api/actions/{id}/screenshot shows where"
    )
    recipe_fixes: list[RecipeFixOut] = Field(
        default_factory=list,
        description="Click recipe fixes the AI made during this action; a proposed one waits for an admin",
    )
    created_at: datetime


class ActionPage(BaseModel):
    items: list[ActionOut]
    total: int


class ActionList(ActionPage):
    counts: dict[ActionStatus, int] = Field(
        description="Actions per status with the same filters except status (tab badges); every status is present"
    )


class NotApproved(BaseModel):
    action: ActionOut
    reason: str


class BatchApproveResult(BaseModel):
    """Approved actions start at once (connector writes) or wait for a person (manual tasks).

    Connector writes whose connection has writes disabled stay ``pending_approval`` and are listed in
    ``not_approved``.
    """

    items: list[ActionOut]
    total: int
    not_approved: list[NotApproved]


class ActionSecret(BaseModel):
    """Returned once; the stored value is wiped by this call."""

    kind: str = Field(examples=["temporary_password"])
    value: str


class OffboardSkipReason(StrEnum):
    SERVICE_ACCOUNT = "service_account"
    ACTION_OPEN = "action_open"


class OffboardSkipped(BaseModel):
    account: AccountRef
    app: AppRef
    reason: OffboardSkipReason


class OffboardResult(BaseModel):
    """The person is marked as left. Actions wait for approval as one batch."""

    batch_id: uuid.UUID
    person: PersonRef
    actions: list[ActionOut]
    skipped: list[OffboardSkipped]


class OnboardApp(BaseModel):
    app_id: uuid.UUID
    role: str | None = Field(default=None, max_length=100, description="Role in the app, e.g. member or admin")


class OnboardRequest(BaseModel):
    """Apps to give the person an account in. A repeated ``app_id`` counts once (the first one)."""

    apps: list[OnboardApp] = Field(min_length=1, max_length=200)
    email: str | None = Field(
        default=None, max_length=320, description="E-mail for the new accounts; defaults to the person's primary e-mail"
    )


class OnboardSkipReason(StrEnum):
    HAS_ACCOUNT = "has_account"
    ACTION_OPEN = "action_open"


class OnboardSkipped(BaseModel):
    app: AppRef
    reason: OnboardSkipReason


class OnboardResult(BaseModel):
    """Actions wait for approval as one batch (``POST /api/actions/batch/{batch_id}/approve``)."""

    batch_id: uuid.UUID
    person: PersonRef
    actions: list[ActionOut]
    skipped: list[OnboardSkipped]
