"""Who is calling: the session cookie or an API token, the admin role and the client header (CSRF).

Every panel route depends on ``require_admin``, ``/api/me`` on ``get_current_user`` (``router.py``). Both
accept a personal API token (``Authorization: Bearer orv_...``, ``services.auth.api_tokens``) instead of
the cookie; a ``read`` token gets only safe methods. Routes that need the cookie itself (sign-in
settings, API tokens) depend on ``get_current_session``. Unsafe methods with the cookie also need the
``X-Open-Revoke-Client`` header: another site cannot set it without a CORS preflight, which the API
refuses, so a cross-site form or ``fetch`` with the user's cookie fails. ``SameSite=Lax`` alone is not
enough here: other ports on ``localhost`` count as the same site. A bearer token needs no such header:
a browser never sends it on its own.
"""

from typing import Annotated

from fastapi import Cookie, Depends, Header, Request

from app.api.deps import SessionDep
from app.models import User, UserSession
from app.models.enums import ApiTokenScope, DecisionVia, UserRole
from app.services.auth import api_tokens, sessions
from app.services.auth.actor import set_actor
from app.services.errors import AuthenticationError, PermissionDeniedError

CLIENT_HEADER = "X-Open-Revoke-Client"
SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS"})

SessionCookie = Annotated[str | None, Cookie(alias=sessions.COOKIE_NAME, include_in_schema=False)]


async def require_client_header(request: Request) -> None:
    if request.method not in SAFE_METHODS and not request.headers.get(CLIENT_HEADER):
        raise PermissionDeniedError(f"Missing the {CLIENT_HEADER} header.")


async def get_optional_session(session: SessionDep, token: SessionCookie = None) -> UserSession | None:
    row = await sessions.find(session, token)
    if row is not None:
        set_actor(row.user.email, row.user.id, DecisionVia.PANEL)  # audit events of this request name the user
    return row


async def get_current_session(
    request: Request, current: Annotated[UserSession | None, Depends(get_optional_session)]
) -> UserSession:
    await require_client_header(request)
    if current is None:
        raise AuthenticationError("Sign in to continue.")
    return current


def bearer_token(authorization: str | None) -> str | None:
    """The token of an ``Authorization: Bearer ...`` header, or None."""
    if not authorization:
        return None
    kind, _, value = authorization.partition(" ")
    if kind.lower() != "bearer":
        return None
    return value.strip() or None


async def get_current_user(
    request: Request,
    session: SessionDep,
    current: Annotated[UserSession | None, Depends(get_optional_session)],
    authorization: Annotated[str | None, Header(include_in_schema=False)] = None,
) -> User:
    """The signed-in user from an API token, else from the session cookie."""
    token = bearer_token(authorization)
    if token is None:
        return (await get_current_session(request, current)).user
    row = await api_tokens.authenticate(session, token)
    if row is None:
        raise AuthenticationError("The API token is not valid. Create a new one in Settings, API and MCP.")
    if row.scope == ApiTokenScope.READ and request.method not in SAFE_METHODS:
        raise PermissionDeniedError("This API token can only read. Create a token with write access to change data.")
    set_actor(api_tokens.actor_name(row), row.user.id, DecisionVia.API)  # audit events name the user and the token
    return row.user


async def require_admin(user: Annotated[User, Depends(get_current_user)]) -> User:
    if user.role != UserRole.ADMIN:
        raise PermissionDeniedError("Only an admin can do this.")
    return user


OptionalSessionDep = Annotated[UserSession | None, Depends(get_optional_session)]
CurrentSessionDep = Annotated[UserSession, Depends(get_current_session)]
CurrentUserDep = Annotated[User, Depends(get_current_user)]
AdminDep = Annotated[User, Depends(require_admin)]
