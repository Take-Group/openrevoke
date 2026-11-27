"""Connect with Google: the admin signs in with Google instead of pasting a service account key.

1. ``start``: the panel sends the company's OAuth client. A random ``state`` with the client, the
   PKCE verifier and the admin's e-mail goes to Redis (encrypted, 10 minutes, single use); the
   panel opens Google's consent screen.
2. ``finish``: Google sends the browser to the callback with ``code`` and ``state``. The callback
   needs no panel session (the redirect URI may be another host than the panel, see
   ``settings.google_oauth_redirect_base``): the single-use ``state`` an admin created proves it.
   The code becomes a refresh token, the admin's e-mail comes from userinfo, and
   ``setup_google_source`` checks the scopes and creates the app and connection.

``finish`` never raises: it returns the panel address with ``google=connected`` or
``google_error=<reason>`` for the Discovery page to show.
"""

import secrets
from dataclasses import dataclass
from typing import TYPE_CHECKING
from urllib.parse import urlencode

import httpx

from app.config import settings
from app.connectors.errors import ConnectorError
from app.connectors.google_workspace import oauth
from app.connectors.http import build_http_client
from app.redis import redis_client
from app.services.auth.actor import current_actor
from app.services.discovery_setup import ensure_no_source, setup_google_source
from app.services.errors import DomainError
from app.services.secret_box import SecretsUnreadableError, decrypt_secrets, encrypt_secrets

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from app.schemas.discovery import GoogleOAuthStart
    from app.services.connector_runtime import HttpFactory
    from app.services.scan_dispatch import ScanDispatcher
    from app.services.sync_dispatch import SyncDispatcher

STATE_TTL_SECONDS = 600
STATE_PREFIX = "open-revoke:google-oauth:"
MAX_ERROR_LENGTH = 400
GOOGLE_ERRORS = {
    "access_denied": "Google sign-in was cancelled, or the account cannot allow these permissions.",
    "admin_policy_enforced": "The Google Workspace admin policy blocks this OAuth client.",
    "org_internal": "The OAuth client is Internal to another Google Workspace. Sign in with an admin of its own.",
}


@dataclass(frozen=True)
class Pending:
    client_id: str
    client_secret: str
    customer: str
    domain: str | None
    verifier: str
    started_by: str


async def start(session: AsyncSession, data: GoogleOAuthStart, started_by: str) -> str:
    """Save the pending sign-in and return Google's consent screen address."""
    await ensure_no_source(session)
    state = secrets.token_urlsafe(32)
    verifier = oauth.new_verifier()
    payload = {
        "client_id": data.client_id.strip(),
        "client_secret": data.client_secret.strip(),
        "customer": data.customer.strip(),
        "domain": (data.domain or "").strip(),
        "verifier": verifier,
        "started_by": started_by,
    }
    token = encrypt_secrets(payload) or b""
    await redis_client.set(STATE_PREFIX + state, token.decode(), ex=STATE_TTL_SECONDS)
    return oauth.authorization_url(payload["client_id"], settings.google_oauth_redirect_uri, state, verifier)


async def finish(
    session: AsyncSession,
    *,
    code: str | None,
    state: str | None,
    error: str | None,
    sync_dispatcher: SyncDispatcher,
    scan_dispatcher: ScanDispatcher,
    http_factory: HttpFactory = build_http_client,
) -> str:
    """Finish the sign-in. Returns the panel address to send the browser to."""
    pending = await _take_pending(state)
    if pending is None:
        return _panel(error="The Google sign-in expired or was already used. Click Connect with Google again.")
    current_actor.set(pending.started_by)  # audit events name the admin who started it
    if error:
        return _panel(error=GOOGLE_ERRORS.get(error, f"Google returned an error: {error}"))
    if not code:
        return _panel(error="Google returned no authorization code.")
    try:
        async with http_factory() as http:
            granted = await oauth.exchange_code(
                http,
                pending.client_id,
                pending.client_secret,
                code,
                pending.verifier,
                settings.google_oauth_redirect_uri,
            )
            admin_email = await oauth.fetch_email(http, granted.token.value)
    except ConnectorError as exc:
        return _panel(error=str(exc))
    except httpx.HTTPError as exc:
        return _panel(error=f"Network error while reaching Google: {exc}")
    config = {
        "admin_email": admin_email,
        "customer": pending.customer,
        "domain": pending.domain,
        "oauth_client_id": pending.client_id,
    }
    credentials = {"oauth_client_secret": pending.client_secret, "oauth_refresh_token": granted.refresh_token}
    try:
        await setup_google_source(session, config, credentials, sync_dispatcher, scan_dispatcher, http_factory)
    except DomainError as exc:
        await session.rollback()
        return _panel(error=exc.message)
    return _panel(connected=True)


async def _take_pending(state: str | None) -> Pending | None:
    if not state or len(state) > 100:
        return None
    raw = await redis_client.getdel(STATE_PREFIX + state)
    if not raw:
        return None
    try:
        values = decrypt_secrets(raw.encode())
    except SecretsUnreadableError:
        return None
    return Pending(
        client_id=values["client_id"],
        client_secret=values["client_secret"],
        customer=values["customer"],
        domain=values["domain"] or None,
        verifier=values["verifier"],
        started_by=values["started_by"],
    )


def _panel(*, connected: bool = False, error: str | None = None) -> str:
    params = {"google": "connected"} if connected else {"google_error": (error or "")[:MAX_ERROR_LENGTH]}
    return f"{settings.public_url}/discovery?{urlencode(params)}"
