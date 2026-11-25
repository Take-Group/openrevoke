"""Can an app's connector perform a write itself, and will it run without a human?

``connector_supports`` decides the kind of a new action: the real write
(``create_account`` / ``delete_account``) when the connector of the app's
connection has the capability, a ``manual_task`` otherwise. It does not look
at ``writes_enabled``: the action is created either way and approval checks
the switch.
"""

from typing import TYPE_CHECKING

from app.connectors.base import Capability
from app.connectors.registry import UnknownConnectorError, get_connector
from app.schemas.actions import WriteMode

if TYPE_CHECKING:
    from app.connectors.base import Connector
    from app.models import Connection
    from app.schemas.actions import WriteKind


def connection_connector(connection: Connection | None) -> Connector | None:
    if connection is None:
        return None
    try:
        return get_connector(connection.connector_key)
    except UnknownConnectorError:
        return None


def connector_supports(connection: Connection | None, kind: WriteKind) -> bool:
    connector = connection_connector(connection)
    return connector is not None and connector.supports(Capability(str(kind)))


def write_mode(connection: Connection | None, kind: WriteKind) -> WriteMode:
    if not connector_supports(connection, kind):
        return WriteMode.MANUAL
    assert connection is not None
    return WriteMode.AUTOMATIC if connection.writes_enabled else WriteMode.WRITES_DISABLED


def delete_suspends(connection: Connection | None) -> bool:
    """True when the connector's delete suspends the account instead (Google Workspace)."""
    connector = connection_connector(connection)
    return connector is not None and connector.delete_suspends
