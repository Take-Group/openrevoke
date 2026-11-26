"""Access tokens for Google APIs: service account with domain-wide delegation, or OAuth (oauth.py).

The JWT assertion (RS256, the service account's private key) is signed with
``cryptography``, httpx exchanges it at the token endpoint: the OAuth 2.0 JWT
bearer flow (RFC 7523) without google-auth and its ASN.1 dependencies.
"""

import base64
import json
import time
from typing import TYPE_CHECKING, Any

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa

from app.connectors.base import ConnectorError, NeedsLogin
from app.connectors.google_workspace import oauth
from app.connectors.http import json_body

if TYPE_CHECKING:
    import httpx

    from app.connectors.base import ConnectorContext

DEFAULT_TOKEN_URI = "https://oauth2.googleapis.com/token"
GRANT_TYPE = "urn:ietf:params:oauth:grant-type:jwt-bearer"
TOKEN_LIFETIME_SECONDS = 3600
# OAuth errors that mean "the credentials or the delegation are wrong", not an outage.
CREDENTIAL_ERRORS = {"invalid_grant", "unauthorized_client", "invalid_client", "access_denied"}


def parse_service_account(value: str) -> dict[str, Any]:
    try:
        info = json.loads(value)
    except ValueError as exc:
        raise ConnectorError("The service account key is not valid JSON") from exc
    if not isinstance(info, dict) or info.get("type") != "service_account":
        raise ConnectorError('The service account key must be a JSON key file with "type": "service_account"')
    for key in ("client_email", "private_key"):
        if not info.get(key):
            raise ConnectorError(f"The service account key has no {key}")
    return info


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _segment(value: dict[str, Any]) -> str:
    return _b64url(json.dumps(value, separators=(",", ":")).encode())


def sign_rs256(private_key_pem: str, header: dict[str, Any], payload: dict[str, Any]) -> str:
    """A compact JWS with RS256. ValueError when the key is not an RSA private key in PEM."""
    key = serialization.load_pem_private_key(private_key_pem.encode(), password=None)
    if not isinstance(key, rsa.RSAPrivateKey):
        raise ValueError("not an RSA private key")
    signing_input = f"{_segment({'typ': 'JWT', 'alg': 'RS256', **header})}.{_segment(payload)}"
    signature = key.sign(signing_input.encode(), padding.PKCS1v15(), hashes.SHA256())
    return f"{signing_input}.{_b64url(signature)}"


def build_assertion(info: dict[str, Any], subject: str, scopes: list[str], now: int | None = None) -> str:
    issued = int(time.time()) if now is None else now
    payload = {
        "iss": info["client_email"],
        "sub": subject,
        "scope": " ".join(scopes),
        "aud": info.get("token_uri") or DEFAULT_TOKEN_URI,
        "iat": issued,
        "exp": issued + TOKEN_LIFETIME_SECONDS,
    }
    header = {"kid": info["private_key_id"]} if info.get("private_key_id") else {}
    return sign_rs256(info["private_key"], header, payload)


async def fetch_access_token(http: httpx.AsyncClient, info: dict[str, Any], subject: str, scopes: list[str]) -> str:
    try:
        assertion = build_assertion(info, subject, scopes)
    except ValueError as exc:
        raise ConnectorError("The service account private key cannot be read") from exc
    response = await http.post(
        info.get("token_uri") or DEFAULT_TOKEN_URI, data={"grant_type": GRANT_TYPE, "assertion": assertion}
    )
    body = json_body(response, "Google OAuth")
    if response.is_success and isinstance(body, dict) and body.get("access_token"):
        return str(body["access_token"])
    error = body.get("error") if isinstance(body, dict) else None
    description = body.get("error_description") if isinstance(body, dict) else None
    message = (
        f"Google refused the service account token ({error or response.status_code}"
        f"{': ' + description if description else ''}). Check the key, the admin e-mail and the "
        f"domain-wide delegation scopes ({', '.join(scopes)})."
    )
    if error in CREDENTIAL_ERRORS or response.status_code == 401:
        raise NeedsLogin(message)
    raise ConnectorError(message)


async def access_token(ctx: ConnectorContext, scope: str) -> str:
    """Token for one scope: service account when a key is set, else the admin's OAuth refresh token."""
    config = ctx.config
    if config.service_account_json is not None:
        info = parse_service_account(config.service_account_json.get_secret_value())
        return await fetch_access_token(ctx.http, info, config.admin_email.strip(), [scope])
    if config.oauth_client_id and config.oauth_client_secret is not None and config.oauth_refresh_token is not None:
        return await oauth.refreshed_token(
            ctx.http,
            config.oauth_client_id,
            config.oauth_client_secret.get_secret_value(),
            config.oauth_refresh_token.get_secret_value(),
            scope,
        )
    raise NeedsLogin("Google Workspace has no credentials. Connect with Google or paste a service account key.")
