"""Pure parsing of SCIM 2.0 responses (RFC 7643, RFC 7644)."""

from dataclasses import dataclass
from typing import Any

from app.connectors.base import ConnectorError, RemoteAccount

USER_SCHEMA = "urn:ietf:params:scim:schemas:core:2.0:User"
PATCH_SCHEMA = "urn:ietf:params:scim:api:messages:2.0:PatchOp"


@dataclass(frozen=True)
class ListPage:
    resources: list[dict[str, Any]]
    total_results: int


def parse_list_response(body: Any) -> ListPage:
    if not isinstance(body, dict):
        raise ConnectorError("The SCIM server returned an unexpected list response")
    # RFC 7644 names it "Resources"; a few servers send "resources".
    resources = body.get("Resources", body.get("resources", []))
    if resources is None:
        resources = []
    if not isinstance(resources, list) or not all(isinstance(item, dict) for item in resources):
        raise ConnectorError("The SCIM server returned Resources that are not a list of objects")
    total = body.get("totalResults")
    if not isinstance(total, int) or total < 0:
        raise ConnectorError("The SCIM server returned no totalResults, so the list cannot be checked for completeness")
    return ListPage(resources=resources, total_results=total)


def primary_email(user: dict[str, Any]) -> str | None:
    """Primary e-mail, else the first one, else ``userName`` when it looks like an e-mail."""
    emails = [entry for entry in user.get("emails") or [] if isinstance(entry, dict) and _clean(entry.get("value"))]
    chosen = next((entry for entry in emails if entry.get("primary") is True), emails[0] if emails else None)
    value = _clean(chosen.get("value")) if chosen else None
    if value:
        return value.lower()
    user_name = _clean(user.get("userName"))
    if user_name and "@" in user_name:
        return user_name.lower()
    return None


def display_name(user: dict[str, Any]) -> str | None:
    if _clean(user.get("displayName")):
        return _clean(user.get("displayName"))
    name = user.get("name") or {}
    if not isinstance(name, dict):
        return None
    if _clean(name.get("formatted")):
        return _clean(name.get("formatted"))
    parts = [_clean(name.get("givenName")), _clean(name.get("familyName"))]
    return " ".join(part for part in parts if part) or None


def role(user: dict[str, Any]) -> str | None:
    roles = [entry for entry in user.get("roles") or [] if isinstance(entry, dict) and _clean(entry.get("value"))]
    chosen = next((entry for entry in roles if entry.get("primary") is True), roles[0] if roles else None)
    return _clean(chosen["value"]) if chosen else None


def user_to_account(user: dict[str, Any]) -> RemoteAccount:
    user_id = user.get("id")
    if user_id is None or str(user_id).strip() == "":
        raise ConnectorError("The SCIM server returned a user without id")
    # "active" is optional in SCIM; a missing value means an active user.
    active = user.get("active", True) is not False
    return RemoteAccount(
        external_id=str(user_id),
        email=primary_email(user),
        display_name=display_name(user),
        username=_clean(user.get("userName")),
        role=role(user),
        status="active" if active else "suspended",
        raw={key: user[key] for key in ("id", "userName", "active", "externalId", "meta") if key in user},
    )


def create_user_body(email: str, first_name: str | None, last_name: str | None) -> dict[str, Any]:
    body: dict[str, Any] = {
        "schemas": [USER_SCHEMA],
        "userName": email,
        "emails": [{"value": email, "type": "work", "primary": True}],
        "active": True,
    }
    if first_name or last_name:
        body["name"] = {key: value for key, value in (("givenName", first_name), ("familyName", last_name)) if value}
        body["displayName"] = " ".join(part for part in (first_name, last_name) if part)
    return body


def deactivate_body() -> dict[str, Any]:
    return {"schemas": [PATCH_SCHEMA], "Operations": [{"op": "replace", "path": "active", "value": False}]}


def _clean(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    return value.strip() or None
