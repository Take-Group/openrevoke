"""Live view of the shared browser on the panel's origin (app/browser/live_proxy.py).

Admins only: whoever watches the live view drives a browser with signed-in admin
sessions of SaaS panels. The routes read the session cookie themselves, because
the panel's session dependency does not apply to WebSockets. The WebSocket also
has to come from a page on the same origin: browsers send cookies with a
WebSocket from any site, and the CORS rules do not cover WebSockets.
"""

from urllib.parse import urlsplit

from fastapi import APIRouter, WebSocket
from fastapi.responses import Response
from starlette.requests import HTTPConnection

from app.api.host_check import host_name
from app.browser import live_proxy
from app.database import async_session
from app.models.enums import UserRole
from app.services.auth import sessions
from app.services.errors import AuthenticationError, NotFoundError, PermissionDeniedError

router = APIRouter(prefix="/api/browser/live", include_in_schema=False)


async def _is_admin(connection: HTTPConnection) -> bool | None:
    """True for an admin, False for another user, None without a session."""
    async with async_session() as session:
        row = await sessions.find(session, connection.cookies.get(sessions.COOKIE_NAME))
        await session.commit()
    if row is None:
        return None
    return row.user.role == UserRole.ADMIN


def _same_origin(websocket: WebSocket) -> bool:
    origin = websocket.headers.get("origin")
    if not origin:
        return False
    # Behind the panel's /api proxy, Host is the API's address and X-Forwarded-Host the panel's.
    forwarded = websocket.headers.get("x-forwarded-host", "").split(",")[0].strip()
    page_host = forwarded or websocket.headers.get("host", "")
    return urlsplit(origin).netloc.lower() == page_host.lower() and bool(host_name(page_host))


@router.get("/{path:path}")
async def get_live_file(path: str, request: HTTPConnection) -> Response:
    admin = await _is_admin(request)
    if admin is None:
        raise AuthenticationError("Sign in to continue.")
    if not admin:
        raise PermissionDeniedError("Only an admin can see the shared browser.")
    if not live_proxy.is_live_file(path):
        raise NotFoundError("Not found")
    file = await live_proxy.fetch_file(path)
    if file is None:
        raise NotFoundError("Not found")
    headers = {
        "X-Content-Type-Options": "nosniff",
        "Cache-Control": "no-store" if path.endswith(".html") else "private, max-age=3600",
        "Content-Security-Policy": "frame-ancestors 'self'",
    }
    return Response(file.content, media_type=file.media_type, headers=headers)


@router.websocket("/websockify")
async def live_socket(websocket: WebSocket) -> None:
    if not _same_origin(websocket) or not await _is_admin(websocket):
        await websocket.close(code=1008)
        return
    await live_proxy.pipe(websocket)
