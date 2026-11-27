"""Pure parsing of chatgpt.com's private API: session, workspaces, users, invites.

Field names are a best guess from the web app (``items``, ``total``,
``email``, ``role`` such as ``account-owner``). Not verified on a real Team
workspace (docs/connectors/chatgpt.md).
"""

from typing import Any

from app.connectors.base import RemoteAccount
from app.connectors.errors import ConnectorError, IncompleteListError, NeedsLogin

NAME = "ChatGPT"
INVITE_PREFIX = "invite:"
ROLES = {
    "account-owner": "owner",
    "account-admin": "admin",
    "standard-user": "member",
    "account-member": "member",
}
WORKSPACE_PLANS = frozenset({"team", "business", "enterprise", "edu"})


def access_token(session: Any) -> str:
    """``accessToken`` of ``/api/auth/session``; the logged-out answer is ``{}``."""
    token = session.get("accessToken") if isinstance(session, dict) else None
    if not isinstance(token, str) or not token:
        raise NeedsLogin("The browser is not logged in to ChatGPT. Log in on the Browser page.")
    return token


def workspaces(body: Any) -> list[dict[str, Any]]:
    """Workspace accounts from ``accounts/check``; personal accounts are left out."""
    accounts = body.get("accounts") if isinstance(body, dict) else None
    if not isinstance(accounts, dict):
        raise ConnectorError(f"{NAME} returned an unexpected accounts response")
    found = []
    for entry in accounts.values():
        account = entry.get("account") if isinstance(entry, dict) else None
        if not isinstance(account, dict) or not account.get("account_id"):
            continue
        structure = str(account.get("structure") or "").lower()
        plan = str(account.get("plan_type") or "").lower()
        if structure == "workspace" or plan in WORKSPACE_PLANS:
            found.append(account)
    return found


def pick_workspace(accounts: list[dict[str, Any]], wanted: str | None) -> str:
    if wanted:
        return wanted
    if len(accounts) == 1:
        return str(accounts[0]["account_id"])
    if not accounts:
        raise ConnectorError("The logged-in ChatGPT account has no Team or Business workspace. Log in as its admin.")
    names = ", ".join(f"{account.get('name')} ({account.get('account_id')})" for account in accounts)
    raise ConnectorError(f"The ChatGPT account has several workspaces; set Workspace ID to one of: {names}")


def parse_page(body: Any, what: str) -> tuple[list[dict[str, Any]], int | None]:
    """Items and the ``total`` the server reports (``None`` when it does not say)."""
    if not isinstance(body, dict) or not isinstance(body.get("items"), list):
        raise ConnectorError(f"{NAME} returned an unexpected {what} response")
    items = body["items"]
    if not all(isinstance(item, dict) for item in items):
        raise ConnectorError(f"{NAME} returned an unexpected {what} response")
    total = body.get("total")
    return items, total if isinstance(total, int) else None


def next_offset(offset: int, items: list[dict[str, Any]], total: int | None, limit: int, what: str) -> int | None:
    """Offset of the next page, or ``None`` when the list is complete."""
    read = offset + len(items)
    if total is None:
        # Without a total, a short page may only mean the server caps the page size: read on to an empty page.
        return read if items else None
    if read >= total:
        return None
    if not items:
        raise IncompleteListError(f"{NAME} stopped returning {what} at {read} of {total}")
    return read


def _email(value: Any) -> str | None:
    return value.strip().lower() if isinstance(value, str) and value.strip() else None


def _role(value: Any) -> str | None:
    return ROLES.get(str(value), str(value)) if value else None


def user_to_account(user: dict[str, Any]) -> RemoteAccount:
    user_id = user.get("id")
    if not user_id:
        raise ConnectorError(f"{NAME} returned a user without id")
    status = "suspended" if user.get("deactivated_time") or user.get("is_deactivated") else "active"
    return RemoteAccount(
        external_id=str(user_id),
        email=_email(user.get("email")),
        display_name=user.get("name") or None,
        username=None,
        role=_role(user.get("role")),
        status=status,  # type: ignore[arg-type]
        raw={key: user[key] for key in ("id", "role", "seat_type", "created_time") if key in user},
    )


def invite_to_account(invite: dict[str, Any]) -> RemoteAccount:
    email = _email(invite.get("email_address") or invite.get("email"))
    invite_key = invite.get("id") or email
    if not invite_key:
        raise ConnectorError(f"{NAME} returned an invite without id and e-mail")
    return RemoteAccount(
        external_id=f"{INVITE_PREFIX}{invite_key}",
        email=email,
        display_name=None,
        username=None,
        role=_role(invite.get("role")),
        status="invited",
        raw={key: invite[key] for key in ("id", "role", "created_time") if key in invite},
    )


def is_invite(external_id: str) -> bool:
    return external_id.startswith(INVITE_PREFIX)


def created_invite(body: Any, email: str) -> RemoteAccount:
    """Account of a new invite from the POST answer; refuses an answer that lists the e-mail as failed."""
    if isinstance(body, dict):
        errored = body.get("errored_emails")
        if isinstance(errored, list) and errored:
            raise ConnectorError(f"{NAME} did not invite {email}: {errored[0]}")
        invites = body.get("account_invites")
        if isinstance(invites, list):
            for invite in invites:
                if isinstance(invite, dict) and _email(invite.get("email_address")) == email.lower():
                    return invite_to_account(invite)
    return invite_to_account({"email_address": email})
