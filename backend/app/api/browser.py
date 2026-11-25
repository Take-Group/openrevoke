"""The shared browser: state for the Browser page and opening login pages."""

from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.auth_deps import CurrentUserDep
from app.api.deps import SessionDep
from app.api.errors import UNAVAILABLE_RESPONSE
from app.browser.provider import BrowserProvider, get_browser_provider
from app.models.enums import UserRole
from app.schemas.browser import BrowserOpenRequest, BrowserPolicyOut, BrowserState, BrowserTab
from app.services import browser

router = APIRouter(prefix="/browser")

# No sign-in: the browser container (not a person) polls this to force-install the admin's
# password manager. It returns only the manager brand and its extension id, nothing sensitive.
# Mounted straight on api_router, so it carries the full /api prefix itself.
public_router = APIRouter(prefix="/api/browser")


@public_router.get("/policy", response_model=BrowserPolicyOut)
async def get_browser_policy(session: SessionDep) -> BrowserPolicyOut:
    """Which password-manager extension the shared browser should force-install, from org settings."""
    return await browser.password_manager_policy(session)


# Tests override get_browser_provider with a fake.
ProviderDep = Annotated[BrowserProvider, Depends(get_browser_provider)]


@router.get("", response_model=BrowserState)
async def get_browser_state(session: SessionDep, provider: ProviderDep, user: CurrentUserDep) -> BrowserState:
    """Whether the browser runs, the live view URL, open tabs and the apps that log in there.

    A browser that is down is ``available=false`` with ``error``, not an HTTP error. ``live_view_url``
    is null for a member: only admins may watch and drive the shared browser.
    """
    state = await browser.browser_state(session, provider)
    if user.role != UserRole.ADMIN:
        state.live_view_url = None
    return state


@router.post("/open", response_model=BrowserTab, responses=UNAVAILABLE_RESPONSE)
async def open_browser_page(data: BrowserOpenRequest, session: SessionDep, provider: ProviderDep) -> BrowserTab:
    """Opens ``url`` or the login page of ``app_id`` in the shared browser and brings the tab to the front.

    A tab already on the same origin is navigated to the page and shown instead of opening another one.
    503 when the browser is down.
    """
    return await browser.open_page(session, provider, data)
