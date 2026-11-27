"""Pure parsing for app discovery: Reports API activities and Directory API tokens.

Reports API ``activities.list`` (applicationName ``token``, event ``authorize``)
says who granted which OAuth client access and when. ``admin`` events
``DELETE_USER`` name the people deleted from the directory. Directory API
``tokens.list`` lists the tokens a user holds now.
"""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from app.connectors.discovery import AppGrant
from app.connectors.errors import ConnectorError

# Google's own clients (devices, Google apps). They are not third-party SaaS. Not a complete list:
# the admin hides anything else with "Ignore" in the panel.
GOOGLE_OWNED_NAMES = frozenset(
    {
        "android",
        "android device",
        "chrome",
        "chromeos",
        "gmail",
        "ios",
        "ios account manager",
        "macos",
        "my account",
        "youtube",
    }
)
GOOGLE_OWNED_PREFIXES = ("google ",)


def is_google_owned(app_name: str | None) -> bool:
    if not app_name:
        return False
    name = " ".join(app_name.lower().split())
    return name in GOOGLE_OWNED_NAMES or name.startswith(GOOGLE_OWNED_PREFIXES)


def parse_page(body: Any, list_key: str, api: str) -> tuple[list[dict[str, Any]], str | None]:
    if not isinstance(body, dict):
        raise ConnectorError(f"Google {api} returned an unexpected response")
    items = body.get(list_key) or []
    if not isinstance(items, list):
        raise ConnectorError(f"Google {api} returned {list_key} that is not a list")
    return [item for item in items if isinstance(item, dict)], body.get("nextPageToken") or None


def activity_time(activity: dict[str, Any]) -> datetime | None:
    """``id.time``: RFC 3339 in responses, epoch seconds in the reference docs. Both are accepted."""
    value = (activity.get("id") or {}).get("time")
    if isinstance(value, int | float) or (isinstance(value, str) and value.isdigit()):
        return datetime.fromtimestamp(int(value), UTC)
    if isinstance(value, str):
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)
    return None


def _parameters(event: dict[str, Any]) -> dict[str, Any]:
    values: dict[str, Any] = {}
    for parameter in event.get("parameters") or []:
        if not isinstance(parameter, dict) or not parameter.get("name"):
            continue
        if "multiValue" in parameter:
            values[parameter["name"]] = [str(item) for item in parameter.get("multiValue") or []]
        else:
            values[parameter["name"]] = parameter.get("value")
    return values


def _email(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    email = value.strip().lower()
    return email if "@" in email else None


@dataclass
class GrantBook:
    """Merges audit events and tokens into one ``AppGrant`` per (client id, e-mail)."""

    grants: dict[tuple[str, str], AppGrant] = field(default_factory=dict)
    skipped_google: int = 0

    def _grant(self, client_id: str, email: str, app_name: str | None) -> AppGrant | None:
        if is_google_owned(app_name):
            self.skipped_google += 1
            return None
        grant = self.grants.get((client_id, email))
        if grant is None:
            grant = AppGrant(client_id=client_id, app_name=app_name, email=email)
            self.grants[(client_id, email)] = grant
        elif app_name and not grant.app_name:
            grant.app_name = app_name
        return grant

    def add_activity(self, activity: dict[str, Any]) -> None:
        email = _email((activity.get("actor") or {}).get("email"))
        at = activity_time(activity)
        if email is None:
            return
        for event in activity.get("events") or []:
            if not isinstance(event, dict) or event.get("name") != "authorize":
                continue
            values = _parameters(event)
            client_id = values.get("client_id")
            if not isinstance(client_id, str) or not client_id:
                continue
            app_name = values.get("app_name") if isinstance(values.get("app_name"), str) else None
            grant = self._grant(client_id, email, app_name)
            if grant is None:
                continue
            scope = values.get("scope")
            _add_scopes(grant, scope if isinstance(scope, list) else [scope] if isinstance(scope, str) else [])
            if at is not None:
                grant.first_seen_at = min(grant.first_seen_at or at, at)
                grant.last_seen_at = max(grant.last_seen_at or at, at)

    def add_token(self, email: str, token: dict[str, Any]) -> None:
        client_id = token.get("clientId")
        if not isinstance(client_id, str) or not client_id:
            return
        display = token.get("displayText")
        grant = self._grant(client_id, email.strip().lower(), display if isinstance(display, str) else None)
        if grant is None:
            return
        grant.token_active = True
        _add_scopes(grant, [str(scope) for scope in token.get("scopes") or []])

    def result(self) -> list[AppGrant]:
        return list(self.grants.values())


def _add_scopes(grant: AppGrant, scopes: list[str]) -> None:
    for scope in scopes:
        if scope and scope not in grant.scopes:
            grant.scopes.append(scope)


def deleted_user(activity: dict[str, Any]) -> tuple[str, datetime] | None:
    """E-mail and time of a ``DELETE_USER`` admin event."""
    at = activity_time(activity)
    for event in activity.get("events") or []:
        if isinstance(event, dict) and event.get("name") == "DELETE_USER":
            email = _email(_parameters(event).get("USER_EMAIL"))
            if email and at:
                return email, at
    return None
