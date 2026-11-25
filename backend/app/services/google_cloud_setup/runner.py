"""One run of the automatic setup (the Temporal activity calls ``run``).

Order: signed-in account, project (reused from the last run), Admin SDK API, consent screen,
OAuth client, Google's consent screen (the admin clicks Allow in the live view), then the same
check and import as Connect with Google (``app.services.google_oauth``).
"""

from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING
from urllib.parse import parse_qs, urlsplit

import structlog

from app.browser.provider import get_browser_provider
from app.config import settings
from app.database import async_session
from app.schemas.discovery import GoogleOAuthStart
from app.schemas.google_cloud_setup import SetupStatus, SetupStep
from app.services import google_oauth
from app.services.errors import DomainError
from app.services.google_cloud_setup import console, state

if TYPE_CHECKING:
    from app.services.scan_dispatch import ScanDispatcher
    from app.services.sync_dispatch import SyncDispatcher

logger = structlog.get_logger()

CONSENT_TIMEOUT_SECONDS = 600
CLIENT_NAME = "Open Revoke"

type Heartbeat = Callable[[], Awaitable[None] | None]


async def run(beat: Heartbeat, sync_dispatcher: SyncDispatcher, scan_dispatcher: ScanDispatcher) -> None:
    current = await state.load()
    if current is None or current.status != SetupStatus.RUNNING:
        return
    provider = get_browser_provider()
    context = await provider.connect()
    page = await context.new_page()
    await page.bring_to_front()

    async def step(key: SetupStep, status: SetupStatus = SetupStatus.RUNNING) -> None:
        current.step = key
        current.status = status
        await state.save(current)
        result = beat()
        if result is not None:
            await result

    try:
        await step(SetupStep.SIGN_IN)
        current.admin_email = await console.signed_in_email(page)
        await step(SetupStep.PROJECT)
        if not current.project_id:
            current.project_id = await console.create_project(page, current.project_name)
            await state.save(current)  # a new run reuses the project
        await step(SetupStep.API)
        await console.enable_admin_api(page, current.project_id)
        await step(SetupStep.CONSENT_SCREEN)
        await console.configure_consent_screen(page, current.project_id, current.project_name, current.admin_email)
        await step(SetupStep.CLIENT)
        redirect_uri = settings.google_oauth_redirect_uri
        client_id, client_secret = await console.create_oauth_client(
            page, current.project_id, CLIENT_NAME, redirect_uri
        )
        async with async_session() as session:
            auth_url = await google_oauth.start(
                session, GoogleOAuthStart(client_id=client_id, client_secret=client_secret), current.started_by
            )
        await step(SetupStep.CONSENT, SetupStatus.WAITING_FOR_CONSENT)
        callback = await console.await_redirect(page, auth_url, redirect_uri, CONSENT_TIMEOUT_SECONDS, beat)
        await step(SetupStep.IMPORT)
        params = console.callback_params(callback)
        async with async_session() as session:
            target = await google_oauth.finish(
                session,
                code=params["code"],
                state=params["state"],
                error=params["error"],
                sync_dispatcher=sync_dispatcher,
                scan_dispatcher=scan_dispatcher,
            )
        result = parse_qs(urlsplit(target).query)
        if result.get("google") == ["connected"]:
            current.status = SetupStatus.CONNECTED
            current.error = None
        else:
            current.status = SetupStatus.FAILED
            current.error = (result.get("google_error") or ["Google Workspace could not be connected."])[0]
    except console.NeedsSignInError as exc:
        current.status = SetupStatus.NEEDS_SIGN_IN
        current.error = str(exc)
    except (console.ConsoleError, DomainError) as exc:
        current.status = SetupStatus.FAILED
        current.error = str(exc)
    except Exception as exc:  # a changed console page: say which step, keep the worker alive
        logger.exception("google_cloud_setup_failed", step=str(current.step))
        current.status = SetupStatus.FAILED
        current.error = (
            f"The Google Cloud console did not behave as expected ({type(exc).__name__}). Use the guided setup."
        )
    await state.save(current)
