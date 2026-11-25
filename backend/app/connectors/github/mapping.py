"""Pure parsing of GitHub REST responses: org members and pending invitations."""

from typing import Any

from app.connectors.base import ConnectorError, RemoteAccount

INVITATION_PREFIX = "invitation:"
INVITATION_ROLES = {"direct_member": "member", "admin": "admin"}


def parse_list(body: Any, what: str) -> list[dict[str, Any]]:
    if not isinstance(body, list) or not all(isinstance(item, dict) for item in body):
        raise ConnectorError(f"GitHub returned an unexpected {what} response")
    return body


def next_page_url(links: dict[str, dict[str, str]]) -> str | None:
    """URL of the next page from httpx's parsed ``Link`` header (``response.links``)."""
    return (links.get("next") or {}).get("url") or None


def member_to_account(member: dict[str, Any], admin_ids: set[str]) -> RemoteAccount:
    member_id = member.get("id")
    login = member.get("login")
    if member_id is None or not login:
        raise ConnectorError("GitHub returned a member without id or login")
    external_id = str(member_id)
    return RemoteAccount(
        external_id=external_id,
        # The members API has no e-mail; a person assigns these accounts by login.
        email=None,
        display_name=None,
        username=login,
        role="admin" if external_id in admin_ids else "member",
        status="active",
        raw={key: member[key] for key in ("id", "login", "type", "site_admin", "html_url") if key in member},
    )


def invitation_to_account(invitation: dict[str, Any]) -> RemoteAccount:
    invitation_id = invitation.get("id")
    if invitation_id is None:
        raise ConnectorError("GitHub returned an invitation without id")
    email = invitation.get("email") or None
    login = invitation.get("login") or None
    role = invitation.get("role")
    return RemoteAccount(
        external_id=f"{INVITATION_PREFIX}{invitation_id}",
        email=email.strip().lower() if isinstance(email, str) else None,
        display_name=None,
        username=login,
        role=INVITATION_ROLES.get(role, role) if isinstance(role, str) else None,
        status="invited",
        raw={key: invitation[key] for key in ("id", "login", "email", "role", "created_at") if key in invitation},
    )


def invitation_id(external_id: str) -> str | None:
    """Invitation id when the account is a pending invitation, else ``None``."""
    if external_id.startswith(INVITATION_PREFIX):
        return external_id.removeprefix(INVITATION_PREFIX)
    return None
