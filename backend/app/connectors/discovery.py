"""App discovery: which third-party apps people sign in to with their work account.

An identity provider (Google Workspace now, Microsoft Entra later) knows
when a person used "Sign in with Google" or granted an app access to their
data. A connector that can read this implements ``AppDiscovery`` and lists
``Capability.DISCOVER_APPS``. Like every connector it only reads and never
writes to the database: ``app.services.discovery_scan`` stores the result.

A sign-in is evidence that the person used the app, not proof of a paid
seat. The panel shows it as such.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from datetime import datetime

    from app.connectors.base import ConnectorContext

DirectoryStatus = Literal["active", "suspended"]


@dataclass
class AppGrant:
    """One person and one third-party app (one OAuth client)."""

    client_id: str
    app_name: str | None
    email: str
    scopes: list[str] = field(default_factory=list)
    # From the audit log: first and last time the person authorized the app in the scanned window.
    first_seen_at: datetime | None = None
    last_seen_at: datetime | None = None
    # From the token inventory: the person still holds a token for the app.
    token_active: bool = False


@dataclass
class DirectoryUser:
    email: str
    status: DirectoryStatus
    aliases: list[str] = field(default_factory=list)


@dataclass
class DiscoveryResult:
    grants: list[AppGrant]
    # Every current user of the directory, so a scan can tell active, suspended and deleted people apart.
    directory: list[DirectoryUser]
    # Primary e-mail of a deleted user and when the deletion happened (audit log, same window).
    deleted_users: dict[str, datetime]
    # Window of the audit log that was read.
    events_from: datetime
    events_until: datetime
    # False when the token inventory could not be read (scope not delegated): token_active is unknown.
    token_inventory: bool
    notes: list[str] = field(default_factory=list)


class AppDiscovery(ABC):
    """Mixin for connectors with ``Capability.DISCOVER_APPS``."""

    # Scopes the admin must delegate for the scan. Shown in the setup guide of the panel.
    discovery_scopes: tuple[str, ...] = ()
    optional_discovery_scopes: tuple[str, ...] = ()

    @abstractmethod
    async def discover_apps(self, ctx: ConnectorContext, since: datetime, until: datetime) -> DiscoveryResult:
        """Read sign-ins between ``since`` and ``until`` and the current token inventory."""
