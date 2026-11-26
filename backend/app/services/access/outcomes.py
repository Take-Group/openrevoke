"""What asking for access returns, shared by the request service, the flow, the panel and the Slack agent."""

import enum
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import uuid


class Outcome(enum.StrEnum):
    IN_PROGRESS = "in_progress"  # approved, the connector is creating the account now
    WAITING_FOR_MANAGER = "waiting_for_manager"  # the person's manager decides first
    WAITING_FOR_APPROVAL = "waiting_for_approval"  # an admin approves the action
    WAITING_FOR_ADMIN = "waiting_for_admin"  # approved manual task: an admin creates the account by hand
    ALREADY_HAS_ACCOUNT = "already_has_account"
    ALREADY_REQUESTED = "already_requested"
    NOT_AVAILABLE = "not_available"  # the app's policy is off


@dataclass(frozen=True)
class RequestResult:
    outcome: Outcome
    app_name: str
    action_id: uuid.UUID | None = None
    note: str | None = None  # waiting for the manager: their name; else why it waits (fallback, writes off)
    request_id: uuid.UUID | None = None


@dataclass(frozen=True)
class SlackOrigin:
    user_id: str
    channel_id: str
    message: str | None
