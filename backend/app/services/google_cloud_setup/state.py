"""Progress of the automatic setup, one record in Redis.

One setup at a time per installation. The panel polls it; the worker writes it step by step.
"""

import json
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime, timedelta

from app.redis import redis_client
from app.schemas.google_cloud_setup import (
    GoogleCloudSetupOut,
    SetupStatus,
    SetupStep,
    SetupStepOut,
    StepState,
)

KEY = "open-revoke:google-cloud-setup"
TTL_SECONDS = 7 * 24 * 3600
# A run that has not written anything for this long is treated as dead (worker restarted).
STALE_AFTER = timedelta(minutes=20)

STEPS: list[tuple[SetupStep, str]] = [
    (SetupStep.SIGN_IN, "Google account in the browser"),
    (SetupStep.PROJECT, "Google Cloud project"),
    (SetupStep.API, "Admin SDK API"),
    (SetupStep.CONSENT_SCREEN, "Consent screen (Internal)"),
    (SetupStep.CLIENT, "OAuth client"),
    (SetupStep.CONSENT, "Admin allows access"),
    (SetupStep.IMPORT, "Check access and import people"),
]
ACTIVE_STATUSES = frozenset({SetupStatus.RUNNING, SetupStatus.WAITING_FOR_CONSENT})


@dataclass
class SetupState:
    status: SetupStatus
    step: SetupStep
    started_by: str
    project_name: str
    started_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    finished_at: str | None = None
    project_id: str | None = None
    admin_email: str | None = None
    error: str | None = None

    @property
    def active(self) -> bool:
        if self.status not in ACTIVE_STATUSES:
            return False
        return datetime.now(UTC) - datetime.fromisoformat(self.updated_at) < STALE_AFTER


async def load() -> SetupState | None:
    raw = await redis_client.get(KEY)
    if not raw:
        return None
    data = json.loads(raw)
    data["status"] = SetupStatus(data["status"])
    data["step"] = SetupStep(data["step"])
    return SetupState(**data)


async def save(state: SetupState) -> None:
    state.updated_at = datetime.now(UTC).isoformat()
    if state.status not in ACTIVE_STATUSES and state.finished_at is None:
        state.finished_at = state.updated_at
    await redis_client.set(KEY, json.dumps(asdict(state)), ex=TTL_SECONDS)


def to_out(state: SetupState | None) -> GoogleCloudSetupOut:
    if state is None:
        steps = [SetupStepOut(key=key, label=label, state=StepState.PENDING) for key, label in STEPS]
        return GoogleCloudSetupOut(
            status=None,
            step=None,
            steps=steps,
            project_id=None,
            admin_email=None,
            error=None,
            started_at=None,
            finished_at=None,
        )
    order = [key for key, _ in STEPS]
    current = order.index(state.step)
    status = state.status if state.active or state.status not in ACTIVE_STATUSES else SetupStatus.FAILED
    steps = []
    for index, (key, label) in enumerate(STEPS):
        if status == SetupStatus.CONNECTED or index < current:
            step_state = StepState.DONE
        elif index == current:
            step_state = (
                StepState.FAILED if status in (SetupStatus.FAILED, SetupStatus.NEEDS_SIGN_IN) else StepState.ACTIVE
            )
        else:
            step_state = StepState.PENDING
        steps.append(SetupStepOut(key=key, label=label, state=step_state))
    error = state.error
    if status == SetupStatus.FAILED and state.status in ACTIVE_STATUSES:
        error = "The setup stopped answering (the worker restarted?). Start it again."
    return GoogleCloudSetupOut(
        status=status,
        step=state.step,
        steps=steps,
        project_id=state.project_id,
        admin_email=state.admin_email,
        error=error,
        started_at=datetime.fromisoformat(state.started_at),
        finished_at=datetime.fromisoformat(state.finished_at) if state.finished_at else None,
    )
