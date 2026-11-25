"""``/api/api-tokens``: the signed-in user's personal API tokens (REST API and MCP server).

Needs a panel session (cookie): a token cannot list, create or revoke tokens.
"""

import uuid

from fastapi import APIRouter, Response, status

from app.api.auth_deps import CurrentSessionDep
from app.api.deps import SessionDep
from app.mcp.address import mcp_url
from app.schemas.api_tokens import ApiTokenCreate, ApiTokenCreated, ApiTokenList, ApiTokenOut
from app.services.auth import api_tokens

router = APIRouter(prefix="/api-tokens")


@router.get("", response_model=ApiTokenList)
async def list_api_tokens(session: SessionDep, current: CurrentSessionDep) -> ApiTokenList:
    """The signed-in user's tokens, newest first, and the MCP server address."""
    rows = await api_tokens.list_for_user(session, current.user)
    return ApiTokenList(items=[ApiTokenOut.model_validate(row) for row in rows], mcp_url=mcp_url())


@router.post("", response_model=ApiTokenCreated, status_code=status.HTTP_201_CREATED)
async def create_api_token(data: ApiTokenCreate, session: SessionDep, current: CurrentSessionDep) -> ApiTokenCreated:
    """A new token acting as the signed-in user. ``secret`` is returned only here."""
    row, secret = await api_tokens.create(session, current.user, name=data.name, scope=data.scope)
    return ApiTokenCreated(token=ApiTokenOut.model_validate(row), secret=secret, mcp_url=mcp_url())


@router.delete("/{token_id}", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
async def revoke_api_token(token_id: uuid.UUID, session: SessionDep, current: CurrentSessionDep) -> Response:
    """Deletes the token; clients using it get 401 from the next request."""
    await api_tokens.revoke(session, current.user, token_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
