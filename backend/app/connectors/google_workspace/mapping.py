"""Pure parsing of Admin SDK Directory API responses (``users.list``, ``users.insert``).

``relations`` and ``organizations`` are standard user fields: ``users.list`` returns them with
``projection=basic`` (which leaves out only custom schema fields) and ``viewType=admin_view``.
"""

from datetime import datetime
from typing import Any

from app.connectors.base import RemoteAccount, RemotePerson, RemoteStatus
from app.connectors.errors import ConnectorError

# Google's "Employee ID" field in the Admin console is an externalId of type "organization".
EMPLOYEE_ID_TYPE = "organization"


def parse_users_page(body: Any) -> tuple[list[dict[str, Any]], str | None]:
    """Return the users of one ``users.list`` page and the next page token."""
    if not isinstance(body, dict):
        raise ConnectorError("Google Workspace returned an unexpected users.list response")
    users = body.get("users", [])
    if not isinstance(users, list):
        raise ConnectorError("Google Workspace returned users that are not a list")
    token = body.get("nextPageToken") or None
    return users, token


def user_status(user: dict[str, Any]) -> RemoteStatus:
    # Archived users keep their data but cannot sign in, like suspended ones.
    if user.get("suspended") or user.get("archived"):
        return "suspended"
    return "active"


def user_role(user: dict[str, Any]) -> str:
    if user.get("isAdmin"):
        return "super_admin"
    if user.get("isDelegatedAdmin"):
        return "delegated_admin"
    return "user"


def user_to_account(user: dict[str, Any]) -> RemoteAccount:
    user_id, email = _id_and_email(user)
    return RemoteAccount(
        external_id=user_id,
        email=email,
        display_name=_full_name(user),
        username=email,
        role=user_role(user),
        status=user_status(user),
        raw=_raw(user),
    )


def user_to_person(user: dict[str, Any]) -> RemotePerson:
    user_id, email = _id_and_email(user)
    name = user.get("name") or {}
    organization = primary_organization(user)
    return RemotePerson(
        external_id=user_id,
        email=email,
        aliases=user_aliases(user),
        first_name=_clean(name.get("givenName")),
        last_name=_clean(name.get("familyName")),
        employee_code=employee_id(user),
        active=user_status(user) == "active",
        raw=_raw(user),
        last_sign_in_at=_time(user.get("lastLoginTime")),
        created_at=_time(user.get("creationTime")),
        manager_email=manager_email(user),
        department=_clean(organization.get("department")),
        job_title=_clean(organization.get("title")),
    )


def manager_email(user: dict[str, Any]) -> str | None:
    """The first ``relations`` entry of type ``manager`` (its ``value`` is the manager's e-mail)."""
    for entry in user.get("relations") or []:
        if isinstance(entry, dict) and entry.get("type") == "manager" and _clean(entry.get("value")):
            return str(_clean(entry.get("value"))).lower()
    return None


def primary_organization(user: dict[str, Any]) -> dict[str, Any]:
    """The ``organizations`` entry marked ``primary``, else the first one; {} without any."""
    entries = [entry for entry in user.get("organizations") or [] if isinstance(entry, dict)]
    return next((entry for entry in entries if entry.get("primary")), entries[0] if entries else {})


def _time(value: object) -> datetime | None:
    """RFC 3339 from the Directory API. Google sends 1970-01-01 for "never signed in"."""
    if not isinstance(value, str) or not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return None if parsed.year < 2000 else parsed


def user_aliases(user: dict[str, Any]) -> list[str]:
    """Aliases, non-editable aliases and secondary addresses, without the primary e-mail."""
    primary = (user.get("primaryEmail") or "").strip().lower()
    found: list[str] = []
    candidates = [*(user.get("aliases") or []), *(user.get("nonEditableAliases") or [])]
    candidates += [entry.get("address") for entry in user.get("emails") or [] if isinstance(entry, dict)]
    for value in candidates:
        if not isinstance(value, str):
            continue
        email = value.strip().lower()
        if email and email != primary and email not in found:
            found.append(email)
    return found


def employee_id(user: dict[str, Any]) -> str | None:
    for entry in user.get("externalIds") or []:
        if isinstance(entry, dict) and entry.get("type") == EMPLOYEE_ID_TYPE and _clean(entry.get("value")):
            return _clean(entry.get("value"))
    return None


def _id_and_email(user: dict[str, Any]) -> tuple[str, str]:
    user_id = user.get("id")
    email = _clean(user.get("primaryEmail"))
    if not user_id or not email:
        raise ConnectorError("Google Workspace returned a user without id or primaryEmail")
    return str(user_id), email.lower()


def _full_name(user: dict[str, Any]) -> str | None:
    name = user.get("name") or {}
    full = _clean(name.get("fullName"))
    if full:
        return full
    parts = [_clean(name.get("givenName")), _clean(name.get("familyName"))]
    return " ".join(part for part in parts if part) or None


# Fields kept in account.raw / person_link.raw. Not the whole user: it may hold
# phone numbers, addresses and recovery e-mails nobody needs here.
RAW_FIELDS = (
    "id",
    "primaryEmail",
    "isAdmin",
    "isDelegatedAdmin",
    "suspended",
    "suspensionReason",
    "archived",
    "orgUnitPath",
    "creationTime",
    "lastLoginTime",
    "isEnrolledIn2Sv",
)


def _raw(user: dict[str, Any]) -> dict[str, Any]:
    return {key: user[key] for key in RAW_FIELDS if key in user}


def _clean(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    return value.strip() or None
