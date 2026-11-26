"""Access requests people sent in Slack or on My access."""

from typing import Annotated

from fastapi import APIRouter, Query

from app.api.auth_deps import CurrentUserDep
from app.api.deps import SessionDep
from app.api.params import Limit, Offset
from app.models.enums import AccessRequestStatus
from app.schemas.slack_agent import AccessRequestPage
from app.services.access import requests as access_requests

router = APIRouter()


@router.get("/access-requests", response_model=AccessRequestPage)
async def list_access_requests(
    session: SessionDep,
    _: CurrentUserDep,
    status_filter: Annotated[AccessRequestStatus | None, Query(alias="status")] = None,
    limit: Limit = 50,
    offset: Offset = 0,
) -> AccessRequestPage:
    """Requests for app accounts from Slack and My access, newest first; ``status`` filters."""
    return await access_requests.list_requests(session, status=status_filter, limit=limit, offset=offset)
