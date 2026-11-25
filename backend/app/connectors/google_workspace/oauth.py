"""Google Workspace through OAuth: an admin signs in with Google and consents, Open Revoke keeps the refresh token.

The alternative to the service account (``auth.py``). Google Cloud organizations created since
3 May 2024 block service account keys by default (``iam.managed.disableServiceAccountKeyCreation``),
so for many companies this is the only way that works without changing a policy. Each installation
uses its own OAuth client (Web application, consent screen "Internal"): Google sends the admin back
to this installation's own address, so a shared client would not work for self-hosting.

API calls run with the admin's own rights. If the admin loses the admin role or is removed, Google
refuses the token and the connection goes to ``needs_login``: connect again with another admin.
"""

import base64
import hashlib
import html
import secrets
import time
from dataclasses import dataclass
from typing import TYPE_CHECKING
from urllib.parse import urlencode

from app.connectors.base import ConnectorError, NeedsLogin
from app.connectors.google_workspace.scopes import SCOPE_AUDIT, SCOPE_READ, SCOPE_TOKENS, SCOPE_WRITE, is_granted
from app.connectors.http import json_body

if TYPE_CHECKING:
    import httpx

AUTHORIZE_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
USERINFO_URL = "https://openidconnect.googleapis.com/v1/userinfo"
IDENTITY_SCOPES = ("openid", "email")
# Read users, suspend a leaver (offboarding), audit log, people's tokens. The admin may untick
# the optional ones on Google's consent screen; each call checks the scope it needs.
API_SCOPES = (SCOPE_READ, SCOPE_WRITE, SCOPE_AUDIT, SCOPE_TOKENS)
REQUIRED_SCOPES = (SCOPE_READ, SCOPE_AUDIT)
REFRESH_MARGIN_SECONDS = 60
NAME = "Google"


@dataclass(frozen=True)
class AccessToken:
    value: str
    scopes: frozenset[str]
    expires_at: float


@dataclass(frozen=True)
class Authorization:
    """Result of the code exchange after the admin consented."""

    refresh_token: str
    token: AccessToken


# Access tokens by connection credentials, so one sync or scan refreshes once, not per call.
_cache: dict[str, AccessToken] = {}


def new_verifier() -> str:
    """PKCE code verifier (RFC 7636): 86 URL-safe characters."""
    return secrets.token_urlsafe(64)


def code_challenge(verifier: str) -> str:
    digest = hashlib.sha256(verifier.encode()).digest()
    return base64.urlsafe_b64encode(digest).decode().rstrip("=")


def authorization_url(client_id: str, redirect_uri: str, state: str, verifier: str) -> str:
    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": " ".join((*IDENTITY_SCOPES, *API_SCOPES)),
        "access_type": "offline",  # a refresh token, so syncs run without the admin
        "prompt": "consent",  # Google returns a refresh token only on a consent screen
        "state": state,
        "code_challenge": code_challenge(verifier),
        "code_challenge_method": "S256",
    }
    return f"{AUTHORIZE_URL}?{urlencode(params)}"


async def exchange_code(
    http: httpx.AsyncClient, client_id: str, client_secret: str, code: str, verifier: str, redirect_uri: str
) -> Authorization:
    data = {
        "grant_type": "authorization_code",
        "code": code,
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uri": redirect_uri,
        "code_verifier": verifier,
    }
    body = await _token_request(http, data)
    refresh_token = body.get("refresh_token")
    if not refresh_token:
        raise ConnectorError("Google returned no refresh token. Remove Open Revoke's access and connect again.")
    token = _access_token(body)
    missing = [scope for scope in REQUIRED_SCOPES if not is_granted(token.scopes, scope)]
    if missing:
        raise ConnectorError(
            f"The admin did not allow {', '.join(missing)}. Connect again and keep these permissions ticked."
        )
    return Authorization(refresh_token=str(refresh_token), token=token)


async def fetch_email(http: httpx.AsyncClient, access_token: str) -> str:
    """E-mail of the admin who consented: the account the API calls run as."""
    response = await http.get(USERINFO_URL, headers={"Authorization": f"Bearer {access_token}"})
    body = json_body(response, NAME)
    email = body.get("email") if isinstance(body, dict) else None
    if not response.is_success or not email or body.get("email_verified") is False:
        raise ConnectorError("Google did not return the admin's verified e-mail address")
    return str(email).strip().lower()


async def refreshed_token(
    http: httpx.AsyncClient, client_id: str, client_secret: str, refresh_token: str, scope: str
) -> str:
    """Access token for ``scope``. ``NeedsLogin`` when Google refuses the refresh token or the scope."""
    key = hashlib.sha256(f"{client_id}\0{refresh_token}".encode()).hexdigest()
    token = _cache.get(key)
    if token is None or token.expires_at - REFRESH_MARGIN_SECONDS < time.time():
        data = {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "client_id": client_id,
            "client_secret": client_secret,
        }
        token = _access_token(await _token_request(http, data))
        _cache[key] = token
    if not is_granted(token.scopes, scope):
        raise NeedsLogin(
            f"The admin did not allow {scope} when connecting Google Workspace. Connect again and allow it."
        )
    return token.value


async def _token_request(http: httpx.AsyncClient, data: dict[str, str]) -> dict:
    response = await http.post(TOKEN_URL, data=data)
    body = json_body(response, "Google OAuth")
    if response.is_success and isinstance(body, dict) and body.get("access_token"):
        return body
    error = body.get("error") if isinstance(body, dict) else None
    raw_description = body.get("error_description") if isinstance(body, dict) else None
    description = " ".join(html.unescape(str(raw_description)).split()) if raw_description else None
    detail = f"{error or response.status_code}{': ' + description if description else ''}"
    if error == "invalid_request" and description and "policy" in description:
        raise ConnectorError(
            f"Google refused the redirect URI ({detail}). Google accepts http only for localhost; "
            "any other address needs https and a public domain."
        )
    if error == "invalid_grant":
        raise NeedsLogin(
            f"Google no longer accepts the saved sign-in ({detail}). The admin revoked access, lost the admin "
            "role, or the OAuth consent screen is External in Testing mode (tokens expire after 7 days). "
            "Connect Google Workspace again."
        )
    if error in ("invalid_client", "unauthorized_client") or response.status_code == 401:
        raise NeedsLogin(f"Google rejected the OAuth client ID or secret ({detail})")
    raise ConnectorError(f"Google OAuth failed ({detail})")


def _access_token(body: dict) -> AccessToken:
    expires_in = body.get("expires_in")
    lifetime = int(expires_in) if isinstance(expires_in, int | str) and str(expires_in).isdigit() else 3600
    return AccessToken(
        value=str(body["access_token"]),
        scopes=frozenset(str(body.get("scope") or "").split()),
        expires_at=time.time() + lifetime,
    )
