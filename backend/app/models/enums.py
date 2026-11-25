"""Enumerations shared by models, schemas and services.

Values are stored as plain strings (varchar with a CHECK constraint), not as
native PostgreSQL enums, so adding a value is a simple migration.
"""

from enum import StrEnum


class PersonStatus(StrEnum):
    ACTIVE = "active"
    LEFT = "left"


class PersonKind(StrEnum):
    HUMAN = "human"
    SERVICE = "service"  # shared mailbox, technical or service account: not a person who can leave


class PersonKindSource(StrEnum):
    AUTO = "auto"  # set by the rules in app.services.person_kind; a sync may change it
    MANUAL = "manual"  # set by an admin; never changed by a sync


class Integration(StrEnum):
    API = "api"
    SCIM = "scim"
    BROWSER = "browser"
    MANUAL = "manual"


class PricingModel(StrEnum):
    PER_SEAT = "per_seat"
    FLAT = "flat"
    FREE = "free"


class BillingPeriod(StrEnum):
    MONTHLY = "monthly"
    YEARLY = "yearly"


class ConnectionStatus(StrEnum):
    OK = "ok"
    NEEDS_LOGIN = "needs_login"
    ERROR = "error"
    NEVER_SYNCED = "never_synced"


class PeopleSourceKind(StrEnum):
    MANUAL = "manual"
    CSV = "csv"


class PersonLinkSource(StrEnum):
    MANUAL = "manual"
    CSV = "csv"
    CONNECTION = "connection"


class AccountStatus(StrEnum):
    ACTIVE = "active"
    INVITED = "invited"
    SUSPENDED = "suspended"
    REMOVED = "removed"


class MatchMethod(StrEnum):
    EMAIL = "email"
    ALIAS = "alias"
    MANUAL = "manual"
    NONE = "none"


class AccountKind(StrEnum):
    PERSON = "person"
    SERVICE = "service"
    UNKNOWN = "unknown"


class SyncRunStatus(StrEnum):
    RUNNING = "running"
    OK = "ok"
    FAILED = "failed"
    NEEDS_LOGIN = "needs_login"


class ActionKind(StrEnum):
    CREATE_ACCOUNT = "create_account"
    DELETE_ACCOUNT = "delete_account"
    MANUAL_TASK = "manual_task"


class ActionStatus(StrEnum):
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    RUNNING = "running"
    VERIFYING = "verifying"
    DONE = "done"
    FAILED = "failed"
    CANCELLED = "cancelled"


class RecipeFixStatus(StrEnum):
    """A step fix proposed by AI repair: ``active`` is used by every run, ``proposed`` waits for an admin."""

    PROPOSED = "proposed"  # an irreversible step: an admin approves before any run uses it
    ACTIVE = "active"
    REJECTED = "rejected"  # rejected by an admin, or reverted after it was active


class ActionReason(StrEnum):
    OFFBOARDING = "offboarding"
    ONBOARDING = "onboarding"
    MANUAL = "manual"
    SELF_SERVICE = "self_service"  # a person asked for access (Slack agent or My access in the panel)


class ScanRunStatus(StrEnum):
    RUNNING = "running"
    OK = "ok"
    FAILED = "failed"


class DiscoveredAppStatus(StrEnum):
    """What the admin decided about an app found by the scan."""

    NEW = "new"
    TRACKED = "tracked"  # linked to an app in Open Revoke
    IGNORED = "ignored"


class DirectoryStatus(StrEnum):
    """State of a signed-in person in the directory at the last scan."""

    ACTIVE = "active"
    SUSPENDED = "suspended"
    DELETED = "deleted"  # not in the directory any more, address of the organisation's domain
    EXTERNAL = "external"  # address outside the directory's domains


class UserRole(StrEnum):
    """Panel user role. Admins see and manage everything; users see only their own access and ask for more."""

    ADMIN = "admin"
    USER = "user"


class UserStatus(StrEnum):
    """Where a panel account is on the way in. Only ``active`` accounts can sign in."""

    PENDING = "pending"  # signed up on /signup, an admin has to approve
    ACTIVE = "active"


class UserTokenKind(StrEnum):
    INVITE = "invite"
    PASSWORD_RESET = "password_reset"


class SelfServicePolicy(StrEnum):
    """What the Slack agent does when a person asks for an account in the app."""

    OFF = "off"  # the agent refuses and names the admins
    APPROVAL = "approval"  # an action waits for an admin's approval
    AUTOMATIC = "automatic"  # the action is approved at once (connector writes still need "Allow writes")


class AccessRequestChannel(StrEnum):
    """Where a person asked for access."""

    SLACK = "slack"  # the Slack agent; the result goes back to the Slack chat
    PANEL = "panel"  # the "My access" page of the panel


class AccessRequestStatus(StrEnum):
    OPEN = "open"  # the action is not finished yet
    DONE = "done"
    FAILED = "failed"
    CANCELLED = "cancelled"  # an admin cancelled or rejected the action


class AiProvider(StrEnum):
    ANTHROPIC = "anthropic"
    OPENAI = "openai"
    OPENROUTER = "openrouter"
    CUSTOM = "custom"  # any OpenAI-compatible endpoint: base URL and API key


class AiReasoningEffort(StrEnum):
    """How hard the model thinks. Anthropic takes all five; OpenAI-compatible APIs low to high."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    XHIGH = "xhigh"
    MAX = "max"


class SlackAgentStatus(StrEnum):
    NOT_CONFIGURED = "not_configured"  # no tokens yet
    DISABLED = "disabled"  # tokens set, the agent is switched off
    CONNECTING = "connecting"
    CONNECTED = "connected"  # Socket Mode connection open
    ERROR = "error"


class PeopleImport(StrEnum):
    """Where the admin said the company's people come from (onboarding, ``/welcome``)."""

    GOOGLE_WORKSPACE = "google_workspace"
    MICROSOFT_365 = "microsoft_365"  # no connector yet: the checklist offers a CSV export
    CSV = "csv"
    MANUAL = "manual"


class ChatPlatform(StrEnum):
    """Where the team talks (onboarding): the Slack agent takes access requests there."""

    SLACK = "slack"
    TEAMS = "teams"  # no agent yet
    NONE = "none"


class PasswordManager(StrEnum):
    """The admin's password manager (onboarding). Its browser extension is force-installed in the
    shared Chromium so the admin signs in to SaaS panels by autofill (skills/backend/browser.md).
    ``1password`` and ``bitwarden`` auto-install; ``other`` means install it by hand; ``none`` none."""

    ONE_PASSWORD = "1password"
    BITWARDEN = "bitwarden"
    OTHER = "other"
    NONE = "none"
