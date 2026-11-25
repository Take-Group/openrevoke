"""Registry of connectors: the catalog the API shows and the lookup the sync uses.

A new connector is one line in ``_connectors()`` (skills/backend/new-connector.md).
"""

from typing import TYPE_CHECKING

from app.config import settings
from app.connectors.browser_fake.connector import BrowserFakeConnector
from app.connectors.chatgpt.connector import ChatGptConnector
from app.connectors.claude.connector import ClaudeConnector
from app.connectors.fake.connector import FakeConnector
from app.connectors.github.connector import GitHubConnector
from app.connectors.google_workspace.connector import GoogleWorkspaceConnector
from app.connectors.scim.connector import ScimConnector
from app.connectors.slack.connector import SlackConnector

if TYPE_CHECKING:
    from app.connectors.base import Connector

_PRODUCTION: tuple[Connector, ...] = (
    GoogleWorkspaceConnector(),
    GitHubConnector(),
    ScimConnector(),
    SlackConnector(),
    ClaudeConnector(),
    ChatGptConnector(),
)
# Development only: test data (fake) and the app's own fake panel through the real browser (browser_fake).
_FAKE: tuple[Connector, ...] = (FakeConnector(), BrowserFakeConnector())


class UnknownConnectorError(LookupError):
    def __init__(self, key: str) -> None:
        super().__init__(f"Unknown connector: {key}")
        self.key = key


def fake_connector_enabled() -> bool:
    return settings.debug or settings.enable_fake_connector


def all_connectors() -> list[Connector]:
    """Connectors in catalog order. The fake ones only in development."""
    connectors = list(_PRODUCTION)
    if fake_connector_enabled():
        connectors.extend(_FAKE)
    return connectors


def get_connector(key: str) -> Connector:
    for connector in all_connectors():
        if connector.key == key:
            return connector
    raise UnknownConnectorError(key)
