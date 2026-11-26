"""Access requests and their decisions: ``/api/access-requests`` (admins) and ``/api/me/approvals`` (managers)."""

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.models.enums import (
    AccessRequestChannel,
    AccessRequestStatus,
    ActionKind,
    ActionStatus,
    DecisionOutcome,
    DecisionStep,
    DecisionVia,
    RequestFallbackReason,
    RequestPolicy,
)
from app.schemas.common import ApiModel, AppRef, MoneyAmount, PersonRef

WaitingFor = Literal["manager", "admin"]


class AccessRequestDecisionOut(ApiModel):
    id: uuid.UUID
    step: DecisionStep
    decision: DecisionOutcome
    decided_by: str = Field(description="E-mail of the panel user, 'e-mail (Slack)', a token name or 'Automatic (...)'")
    decided_by_user_id: uuid.UUID | None
    via: DecisionVia
    override: bool = Field(description="An admin decided for the manager")
    comment: str | None
    decided_at: datetime


class AccessRequestOut(BaseModel):
    id: uuid.UUID
    person: PersonRef
    app: AppRef
    action_id: uuid.UUID | None
    action_status: ActionStatus | None
    channel: AccessRequestChannel = Field(description="slack: asked the Slack agent; panel: the panel or the API")
    status: AccessRequestStatus
    waiting_for: WaitingFor | None = Field(description="Who decides next; null when nobody (approved or closed)")
    approver: PersonRef | None = Field(description="The manager the request waits for (or waited for)")
    fallback_reason: RequestFallbackReason | None = Field(
        description="Why an admin decides instead of the manager: no_manager, manager_left, manager_no_access, "
        "manager_is_requester"
    )
    justification: str | None
    role: str | None
    message: str | None
    requested_by: str | None = Field(description="Who asked: panel user e-mail, 'e-mail (Slack)' or a token name")
    on_behalf: bool = Field(description="The person's manager asked for them")
    rejection_comment: str | None = Field(description="Why it was rejected, when it was")
    created_at: datetime
    closed_at: datetime | None
    notified_at: datetime | None


class AccessRequestActionOut(BaseModel):
    id: uuid.UUID
    kind: ActionKind
    status: ActionStatus
    approved_by: str | None
    approved_at: datetime | None
    finished_at: datetime | None
    error: str | None


class AccessRequestDetail(AccessRequestOut):
    policy: RequestPolicy = Field(description="The app's request policy now")
    seat_monthly_cost: MoneyAmount | None = Field(description="Price of one seat per month in the app's currency")
    decisions: list[AccessRequestDecisionOut] = Field(description="Oldest first")
    action: AccessRequestActionOut | None


class AccessRequestPage(BaseModel):
    items: list[AccessRequestOut]
    total: int


class AccessRequestDecisionCreate(BaseModel):
    comment: str | None = Field(
        default=None, max_length=2000, description="Required to reject; shown to the person who asked"
    )


class MyApprovals(AccessRequestPage):
    pending: int = Field(description="Requests waiting for the signed-in user's decision")
    has_reports: bool = Field(description="Someone has the signed-in user as their manager")
