"""Start and read the automatic setup (API side). The work runs in the worker (``runner.run``)."""

from typing import TYPE_CHECKING

from app.config import settings
from app.schemas.google_cloud_setup import GoogleCloudSetupOut, SetupStatus, SetupStep
from app.services.discovery_setup import ensure_no_source
from app.services.errors import ConflictError
from app.services.google_cloud_setup import state

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from sqlalchemy.ext.asyncio import AsyncSession

    from app.schemas.google_cloud_setup import GoogleCloudSetupStart


async def current() -> GoogleCloudSetupOut:
    return state.to_out(await state.load())


async def start(
    session: AsyncSession,
    data: GoogleCloudSetupStart,
    started_by: str,
    dispatch: Callable[[], Awaitable[None]],
) -> GoogleCloudSetupOut:
    """New run. Reuses the project of the last run, so a retry does not create another one."""
    await ensure_no_source(session)
    previous = await state.load()
    if previous is not None and previous.active:
        raise ConflictError("The automatic setup is already running.")
    run = state.SetupState(
        status=SetupStatus.RUNNING,
        step=SetupStep.SIGN_IN,
        started_by=started_by,
        project_name=data.project_name.strip(),
        project_id=(previous.project_id if previous else None) or settings.google_cloud_project_id,
    )
    await state.save(run)
    await dispatch()
    return state.to_out(run)
