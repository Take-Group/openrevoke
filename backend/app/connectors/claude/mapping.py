"""Pure parsing of claude.ai's private API: organizations, members, invites.

Field names are a best guess from the web app (``account.uuid``,
``email_address``, ``role``). Not verified on a real Team organization
(docs/connectors/claude-team.md). Parsers accept a bare list or an object with a
list, and refuse a page that says there is more, so a changed API ends in an
error instead of a partial list.
"""

from typing import Any

from app.connectors.base import ConnectorError, IncompleteListError, RemoteAccount

NAME = "Claude"
INVITE_PREFIX = "invite:"
# Organizations that have seats to manage: Team and Enterprise.
TEAM_CAPABILITIES = frozenset({"raven", "claude_team", "claude_enterprise", "enterprise"})
TEAM_TYPES = frozenset({"team", "enterprise"})
LIST_KEYS = ("members", "invites", "data", "items", "results")
ROLES = {"primary_owner": "owner", "owner": "owner", "admin": "admin", "user": "member", "member": "member"}
PENDING_STATES = frozenset({"pending", "sent", "created"})


def parse_list(body: Any, what: str) -> list[dict[str, Any]]:
    items: Any = body
    if isinstance(body, dict):
        if body.get("has_more") or body.get("next_cursor") or body.get("next_page"):
            raise IncompleteListError(f"{NAME} returned the {what} list in pages, which this connector cannot read")
        items = next((body[key] for key in LIST_KEYS if isinstance(body.get(key), list)), None)
    if not isinstance(items, list) or not all(isinstance(item, dict) for item in items):
        raise ConnectorError(f"{NAME} returned an unexpected {what} response")
    return items


def is_team_org(org: dict[str, Any]) -> bool:
    capabilities = org.get("capabilities")
    if isinstance(capabilities, list) and TEAM_CAPABILITIES & {str(item) for item in capabilities}:
        return True
    return str(org.get("raven_type") or "").lower() in TEAM_TYPES


def pick_organization(orgs: list[dict[str, Any]], wanted: str | None) -> dict[str, Any]:
    """The org from the config, or the only Team/Enterprise org of the logged-in account."""
    if wanted:
        for org in orgs:
            if org.get("uuid") == wanted:
                return org
        raise ConnectorError(f"The logged-in Claude account has no organization {wanted}")
    teams = [org for org in orgs if is_team_org(org)]
    if len(teams) == 1:
        return teams[0]
    if not teams:
        raise ConnectorError(
            "The logged-in Claude account has no Team or Enterprise organization. Log in as an admin of one."
        )
    names = ", ".join(f"{org.get('name')} ({org.get('uuid')})" for org in teams)
    raise ConnectorError(f"The Claude account has several Team organizations; set Organization ID to one of: {names}")


def _role(value: Any) -> str | None:
    return ROLES.get(str(value), str(value)) if value else None


def _email(value: Any) -> str | None:
    return value.strip().lower() if isinstance(value, str) and value.strip() else None


def member_to_account(member: dict[str, Any]) -> RemoteAccount:
    account = member.get("account") if isinstance(member.get("account"), dict) else member
    account_id = account.get("uuid")
    if not account_id:
        raise ConnectorError(f"{NAME} returned a member without account uuid")
    return RemoteAccount(
        external_id=str(account_id),
        email=_email(account.get("email_address") or account.get("email")),
        display_name=account.get("full_name") or account.get("display_name") or account.get("name") or None,
        username=None,
        role=_role(member.get("role")),
        status="active",
        raw={"uuid": account_id, "role": member.get("role"), "created_at": member.get("created_at")},
    )


def is_pending(invite: dict[str, Any]) -> bool:
    status = invite.get("status")
    return status is None or str(status).lower() in PENDING_STATES


def invite_to_account(invite: dict[str, Any]) -> RemoteAccount:
    invite_id = invite.get("uuid") or invite.get("id")
    if not invite_id:
        raise ConnectorError(f"{NAME} returned an invite without uuid")
    return RemoteAccount(
        external_id=f"{INVITE_PREFIX}{invite_id}",
        email=_email(invite.get("email_address") or invite.get("email")),
        display_name=None,
        username=None,
        role=_role(invite.get("role")),
        status="invited",
        raw={"uuid": invite_id, "role": invite.get("role"), "status": invite.get("status")},
    )


def invite_id(external_id: str) -> str | None:
    return external_id.removeprefix(INVITE_PREFIX) if external_id.startswith(INVITE_PREFIX) else None


def created_invite(body: Any, email: str) -> RemoteAccount:
    """Account of a new invite from the POST answer: one invite, or a list with it."""
    candidates = body if isinstance(body, list) else [body]
    if isinstance(body, dict):
        candidates = next((body[key] for key in LIST_KEYS if isinstance(body.get(key), list)), [body])
    for item in candidates:
        if isinstance(item, dict) and (item.get("uuid") or item.get("id")):
            return invite_to_account(item)
    return RemoteAccount(
        external_id=f"{INVITE_PREFIX}{email.lower()}",
        email=email.lower(),
        display_name=None,
        username=None,
        role=None,
        status="invited",
    )
