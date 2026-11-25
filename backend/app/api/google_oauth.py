"""Connect with Google (services/google_oauth.py): start in the panel, callback from Google."""

from typing import Annotated

from fastapi import APIRouter, Query, status
from fastapi.responses import RedirectResponse

from app.api.auth_deps import AdminDep
from app.api.deps import DispatcherDep, ScanDispatcherDep, SessionDep
from app.schemas.discovery import GoogleOAuthStart, GoogleOAuthStartOut
from app.services import google_oauth

# Needs a signed-in admin (included in the panel router).
router = APIRouter()
# No panel session: Google sends the browser here, possibly on another host than the panel.
# The single-use state from ``start`` authorizes the request.
callback_router = APIRouter(prefix="/api")


@router.post("/discovery/google-oauth/start", response_model=GoogleOAuthStartOut)
async def start_google_oauth(data: GoogleOAuthStart, session: SessionDep, admin: AdminDep) -> GoogleOAuthStartOut:
    """Address of Google's consent screen for the company's OAuth client. 409 when Google is already connected."""
    url = await google_oauth.start(session, data, admin.email)
    return GoogleOAuthStartOut(authorization_url=url)


@callback_router.get("/discovery/google-oauth/callback", status_code=status.HTTP_303_SEE_OTHER, tags=["discovery"])
async def google_oauth_callback(
    session: SessionDep,
    dispatcher: DispatcherDep,
    scan_dispatcher: ScanDispatcherDep,
    code: Annotated[str | None, Query(max_length=2000)] = None,
    state: Annotated[str | None, Query(max_length=200)] = None,
    error: Annotated[str | None, Query(max_length=200)] = None,
) -> RedirectResponse:
    """Google's redirect after consent. Sends the browser to ``/discovery`` with ``google=connected`` or
    ``google_error``."""
    target = await google_oauth.finish(
        session, code=code, state=state, error=error, sync_dispatcher=dispatcher, scan_dispatcher=scan_dispatcher
    )
    return RedirectResponse(target, status_code=status.HTTP_303_SEE_OTHER)
