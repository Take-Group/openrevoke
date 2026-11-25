"""Who is calling: the session cookie, the admin role and the client header (CSRF).

Every panel route depends on ``require_admin``, ``/api/me`` on ``get_current_session`` (``router.py``). Unsafe
methods also need the ``X-Open-Revoke-Client`` header: another site cannot
set it without a CORS preflight, which the API refuses, so a cross-site form
or ``fetch`` with the user's cookie fails. ``SameSite=Lax`` alone is not
enough here: other ports on ``localhost`` count as the same site.
"""

from typing import Annotated

from fastapi import Cookie, Depends, Request

from app.api.deps import SessionDep
from app.models import User, UserSession
from app.models.enums import UserRole
from app.services.auth import sessions
from app.services.auth.actor import current_actor
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
        current_actor.set(row.user.email)  # audit events of this request name the user
    return row


async def get_current_session(
    request: Request, current: Annotated[UserSession | None, Depends(get_optional_session)]
) -> UserSession:
    await require_client_header(request)
    if current is None:
        raise AuthenticationError("Sign in to continue.")
    return current


async def get_current_user(current: Annotated[UserSession, Depends(get_current_session)]) -> User:
    return current.user


async def require_admin(user: Annotated[User, Depends(get_current_user)]) -> User:
    if user.role != UserRole.ADMIN:
        raise PermissionDeniedError("Only an admin can do this.")
    return user


OptionalSessionDep = Annotated[UserSession | None, Depends(get_optional_session)]
CurrentSessionDep = Annotated[UserSession, Depends(get_current_session)]
CurrentUserDep = Annotated[User, Depends(get_current_user)]
AdminDep = Annotated[User, Depends(require_admin)]
