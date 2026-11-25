"""Language model of the agents (Slack agent). Reading needs a signed-in user, changes the admin role."""

from fastapi import APIRouter

from app.api.auth_deps import AdminDep, CurrentUserDep
from app.api.deps import SessionDep
from app.schemas.ai import AiModelList, AiModelsRequest, AiSettingsOut, AiSettingsUpdate, AiTestResult
from app.services import ai_settings

router = APIRouter()


@router.get("/ai-settings", response_model=AiSettingsOut)
async def get_ai_settings(session: SessionDep, _: CurrentUserDep) -> AiSettingsOut:
    return ai_settings.settings_out(await ai_settings.get_row(session))


@router.put("/ai-settings", response_model=AiSettingsOut)
async def save_ai_settings(data: AiSettingsUpdate, session: SessionDep, _: AdminDep) -> AiSettingsOut:
    return await ai_settings.save(session, data)


@router.post("/ai-settings/models", response_model=AiModelList)
async def list_ai_models(data: AiModelsRequest, session: SessionDep, _: AdminDep) -> AiModelList:
    """Models the key can use, from the provider's API. 400 with the provider's error."""
    return await ai_settings.list_models(session, data)


@router.post("/ai-settings/test", response_model=AiTestResult)
async def test_ai_settings(session: SessionDep, _: AdminDep) -> AiTestResult:
    """One short call with the saved settings."""
    return await ai_settings.test(session)
