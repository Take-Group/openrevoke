"""Automatic Google Cloud setup (services/google_cloud_setup): start it and poll its progress."""

from fastapi import APIRouter, status

from app.api.auth_deps import AdminDep
from app.api.deps import SessionDep
from app.schemas.google_cloud_setup import GoogleCloudSetupOut, GoogleCloudSetupStart
from app.services.google_cloud_setup import service
from app.temporal.google_setup_dispatcher import start_google_cloud_setup

router = APIRouter()


@router.get("/discovery/google-cloud-setup", response_model=GoogleCloudSetupOut)
async def get_google_cloud_setup() -> GoogleCloudSetupOut:
    """Progress of the automatic setup; ``status`` null before the first run. Poll while it runs."""
    return await service.current()


@router.post("/discovery/google-cloud-setup", response_model=GoogleCloudSetupOut, status_code=status.HTTP_202_ACCEPTED)
async def start_google_cloud_setup_run(
    session: SessionDep, admin: AdminDep, data: GoogleCloudSetupStart | None = None
) -> GoogleCloudSetupOut:
    """Opens the Google Cloud console in the shared browser and sets up the OAuth client there.

    The admin must be signed in to Google in that browser. 409 when a run is going or Google
    Workspace is already connected.
    """
    return await service.start(session, data or GoogleCloudSetupStart(), admin.email, start_google_cloud_setup)
