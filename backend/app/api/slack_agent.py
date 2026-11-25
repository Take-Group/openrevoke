"""Slack bot setup. Reading needs a signed-in user, changes the admin role."""

from typing import Annotated
from urllib.parse import urlencode

from fastapi import APIRouter, File, UploadFile, status
from fastapi.responses import RedirectResponse

from app.api.auth_deps import AdminDep, CurrentUserDep
from app.api.deps import SessionDep
from app.schemas.slack_agent import (
    SlackAgentOut,
    SlackAgentUpdate,
    SlackAppCreate,
    SlackTokensUpdate,
)
from app.services import slack_agent_setup
from app.services.errors import InvalidInputError

router = APIRouter()
SETTINGS_PAGE = "/settings/slack"


@router.get("/slack-agent", response_model=SlackAgentOut)
async def get_slack_agent(session: SessionDep, _: CurrentUserDep) -> SlackAgentOut:
    """State of the Slack agent: app created, tokens saved, enabled, workspace."""
    return await slack_agent_setup.state(session)


@router.post("/slack-agent/app", response_model=SlackAgentOut, status_code=status.HTTP_201_CREATED)
async def create_slack_app(data: SlackAppCreate, session: SessionDep, _: AdminDep) -> SlackAgentOut:
    """Creates the Slack app from the manifest with an app configuration token and sets its icon."""
    return await slack_agent_setup.create_app(session, data)


@router.put("/slack-agent/tokens", response_model=SlackAgentOut)
async def save_slack_tokens(data: SlackTokensUpdate, session: SessionDep, _: AdminDep) -> SlackAgentOut:
    """Bot token and app-level token, each checked with Slack first."""
    return await slack_agent_setup.save_tokens(session, data)


@router.patch("/slack-agent", response_model=SlackAgentOut)
async def update_slack_agent(data: SlackAgentUpdate, session: SessionDep, _: AdminDep) -> SlackAgentOut:
    """Turns the Slack agent on or off (``enabled``)."""
    return await slack_agent_setup.update(session, data)


@router.delete("/slack-agent", status_code=status.HTTP_204_NO_CONTENT)
async def remove_slack_agent(session: SessionDep, _: AdminDep) -> None:
    """Forgets the app and its tokens. The app itself stays in Slack."""
    await slack_agent_setup.remove(session)


@router.post("/slack-agent/avatar", response_model=SlackAgentOut)
async def set_slack_avatar(
    session: SessionDep, _: AdminDep, file: Annotated[UploadFile | None, File()] = None
) -> SlackAgentOut:
    """PNG or JPEG, 512-2000 px square. Without a file: the default icon."""
    image = await file.read() if file is not None else None
    return await slack_agent_setup.set_avatar(session, image, file.content_type if file else None)


@router.get("/slack-agent/oauth/start", response_class=RedirectResponse, status_code=status.HTTP_307_TEMPORARY_REDIRECT)
async def start_slack_oauth(session: SessionDep, _: AdminDep) -> RedirectResponse:
    """Sends the admin's browser to Slack's "Allow" page; Slack comes back to the callback."""
    return RedirectResponse(await slack_agent_setup.start_oauth(session))


@router.get(
    "/slack-agent/oauth/callback", response_class=RedirectResponse, status_code=status.HTTP_307_TEMPORARY_REDIRECT
)
async def finish_slack_oauth(
    session: SessionDep,
    _: AdminDep,
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
) -> RedirectResponse:
    """Saves the bot token, then returns to the settings page with ``installed=1`` or ``error=…``."""
    if error or not code or not state:
        return _back({"error": error or "Slack did not return a code"})
    try:
        await slack_agent_setup.finish_oauth(session, code, state)
    except InvalidInputError as exc:
        return _back({"error": exc.message})
    return _back({"installed": "1"})


def _back(query: dict[str, str]) -> RedirectResponse:
    return RedirectResponse(f"{SETTINGS_PAGE}?{urlencode(query)}", status_code=status.HTTP_303_SEE_OTHER)
