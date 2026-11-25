"""First steps of a new installation: the /welcome questions and the dashboard checklist."""

from fastapi import APIRouter

from app.api.auth_deps import AdminDep, CurrentUserDep
from app.api.deps import SessionDep
from app.schemas.setup_checklist import OnboardingChoices, OnboardingOut
from app.services import setup_checklist

router = APIRouter(prefix="/onboarding")


@router.get("", response_model=OnboardingOut)
async def get_onboarding(session: SessionDep, _: CurrentUserDep) -> OnboardingOut:
    """The /welcome answers and the setup checklist, worked out from the data."""
    return await setup_checklist.overview(session)


@router.put("/choices", response_model=OnboardingOut)
async def save_onboarding_choices(data: OnboardingChoices, session: SessionDep, _: AdminDep) -> OnboardingOut:
    """Where people come from and where the team talks. A missing field keeps the earlier answer."""
    return await setup_checklist.save_choices(session, data)


@router.post("/dismiss", response_model=OnboardingOut)
async def dismiss_onboarding(session: SessionDep, _: AdminDep) -> OnboardingOut:
    """Hides the setup checklist on the dashboard."""
    return await setup_checklist.dismiss(session)
