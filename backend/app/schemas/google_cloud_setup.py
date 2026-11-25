"""Automatic Google Cloud setup: Open Revoke clicks through the Google Cloud console in the shared browser."""

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class SetupStatus(StrEnum):
    RUNNING = "running"
    NEEDS_SIGN_IN = "needs_sign_in"  # nobody is signed in to Google in the shared browser
    WAITING_FOR_CONSENT = "waiting_for_consent"  # the admin clicks Allow in the live view
    CONNECTED = "connected"
    FAILED = "failed"


class SetupStep(StrEnum):
    SIGN_IN = "sign_in"
    PROJECT = "project"
    API = "api"
    CONSENT_SCREEN = "consent_screen"
    CLIENT = "client"
    CONSENT = "consent"
    IMPORT = "import"


class StepState(StrEnum):
    PENDING = "pending"
    ACTIVE = "active"
    DONE = "done"
    FAILED = "failed"


class SetupStepOut(BaseModel):
    key: SetupStep
    label: str
    state: StepState


class GoogleCloudSetupOut(BaseModel):
    """Progress of the automatic setup. ``status`` is null before the first run."""

    status: SetupStatus | None
    step: SetupStep | None
    steps: list[SetupStepOut]
    project_id: str | None = Field(description="Google Cloud project used; a new run reuses it")
    admin_email: str | None = Field(description="Google account signed in to the shared browser")
    error: str | None
    started_at: datetime | None
    finished_at: datetime | None


class GoogleCloudSetupStart(BaseModel):
    project_name: str = Field(default="Open Revoke", min_length=4, max_length=30)
