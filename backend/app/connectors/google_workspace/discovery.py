"""App discovery for Google Workspace (docs/connectors/google_workspace.md, section "Skan aplikacji").

Three reads, all with the credentials of the connection (``auth.access_token``):

1. Reports API, ``token`` events ``authorize``: who authorized which OAuth
   client, and when. Google keeps at most 180 days. Required scope
   ``admin.reports.audit.readonly``.
2. Reports API, ``admin`` events ``DELETE_USER``: people deleted from the
   directory in the same window. Same scope.
3. Directory API ``tokens.list`` per user: tokens people hold now, also for
   apps authorized before the window. Scope ``admin.directory.user.security``
   is optional: without it the scan says so and goes on.
"""

import asyncio
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from app.connectors.discovery import DirectoryUser
from app.connectors.errors import ConnectorError, NeedsLogin
from app.connectors.google_workspace import discovery_mapping, mapping
from app.connectors.google_workspace.auth import access_token
from app.connectors.google_workspace.scopes import SCOPE_AUDIT, SCOPE_TOKENS
from app.connectors.http import check_page_limit, json_body, raise_for_app_error

if TYPE_CHECKING:
    from app.connectors.base import ConnectorContext

REPORTS_API = "https://admin.googleapis.com/admin/reports/v1/activity/users/all/applications"
DIRECTORY_API = "https://admin.googleapis.com/admin/directory/v1"
REPORTS_PAGE_SIZE = 1000
TOKEN_CONCURRENCY = 8
NAME = "Google Workspace"


def rfc3339(value: datetime) -> str:
    return value.astimezone(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")


async def audit_token(ctx: ConnectorContext) -> str:
    try:
        return await access_token(ctx, SCOPE_AUDIT)
    except NeedsLogin as exc:
        raise ConnectorError(
            f"Google refused the audit log scope {SCOPE_AUDIT}. Allow it when you connect with Google, or add it "
            f"to the domain-wide delegation of the service account, then scan again. Details: {exc}"
        ) from exc


async def read_activities(
    ctx: ConnectorContext, token: str, application: str, event: str, since: datetime, until: datetime
) -> list[dict[str, Any]]:
    """All activities of one event in the window, every page or an error."""
    activities: list[dict[str, Any]] = []
    page_token: str | None = None
    pages = 0
    while True:
        pages += 1
        check_page_limit(pages, NAME)
        params: dict[str, str | int] = {
            "eventName": event,
            "startTime": rfc3339(since),
            "endTime": rfc3339(until),
            "maxResults": REPORTS_PAGE_SIZE,
        }
        if ctx.config.customer and ctx.config.customer != "my_customer":
            params["customerId"] = ctx.config.customer
        if page_token:
            params["pageToken"] = page_token
        response = await ctx.http.get(f"{REPORTS_API}/{application}", params=params, headers=_auth(token))
        raise_for_app_error(response, f"{NAME} Reports API", auth_statuses=(401,))
        items, page_token = discovery_mapping.parse_page(json_body(response, NAME), "items", "Reports API")
        activities.extend(items)
        if not page_token:
            return activities


async def read_user_tokens(ctx: ConnectorContext, token: str, email: str) -> list[dict[str, Any]]:
    response = await ctx.http.get(f"{DIRECTORY_API}/users/{email}/tokens", headers=_auth(token))
    if response.status_code == 404:
        return []  # the user was deleted while the scan ran
    raise_for_app_error(response, f"{NAME} tokens.list")
    items, _ = discovery_mapping.parse_page(json_body(response, NAME), "items", "tokens.list")
    return items


async def read_token_inventory(
    ctx: ConnectorContext, emails: list[str], book: discovery_mapping.GrantBook
) -> str | None:
    """Add every user's tokens to ``book``. Returns a note when the inventory was skipped."""
    try:
        token = await access_token(ctx, SCOPE_TOKENS)
    except NeedsLogin:
        return (
            f"Token inventory skipped: the scope {SCOPE_TOKENS} is not allowed. Only sign-ins from the "
            "audit log were read, so apps authorized more than 180 days ago may be missing."
        )
    limit = asyncio.Semaphore(TOKEN_CONCURRENCY)

    async def one(email: str) -> tuple[str, list[dict[str, Any]]]:
        async with limit:
            return email, await read_user_tokens(ctx, token, email)

    for email, tokens in await asyncio.gather(*(one(email) for email in emails)):
        for item in tokens:
            book.add_token(email, item)
    return None


def directory_users(users: list[dict[str, Any]]) -> list[DirectoryUser]:
    result = []
    for user in users:
        email = (user.get("primaryEmail") or "").strip().lower()
        if email:
            status = "suspended" if mapping.user_status(user) == "suspended" else "active"
            result.append(DirectoryUser(email=email, status=status, aliases=mapping.user_aliases(user)))
    return result


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}
