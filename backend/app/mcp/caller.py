"""Who calls the MCP server: the API token of the request, checked once per HTTP request."""

from contextvars import ContextVar
from dataclasses import dataclass
from typing import TYPE_CHECKING

from app.api.auth_deps import bearer_token
from app.database import async_session
from app.services.auth import api_tokens

if TYPE_CHECKING:
    from app.models.enums import ApiTokenScope, UserRole


@dataclass(frozen=True)
class Caller:
    token: str  # passed on to the API, which checks it again for every tool call
    email: str
    role: UserRole
    scope: ApiTokenScope
    tags: frozenset[str] | None  # ``?tags=people,apps`` on the MCP URL: only these tools


current_caller: ContextVar[Caller | None] = ContextVar("mcp_caller", default=None)


async def authenticate(authorization: str | None, tags: str | None) -> Caller | None:
    token = bearer_token(authorization)
    async with async_session() as session:
        row = await api_tokens.authenticate(session, token)
        if row is None or token is None:
            return None
        await session.commit()  # last_used_at
        chosen = frozenset(tag.strip() for tag in tags.split(",") if tag.strip()) if tags else None
        return Caller(token=token, email=row.user.email, role=row.user.role, scope=row.scope, tags=chosen or None)
