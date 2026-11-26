"""Who calls the MCP server: the API token of the request, checked once per HTTP request.

A request without a token is ``ANONYMOUS``: it may connect and list the tools (so anyone, a
registry included, can read what the server offers), but ``McpEndpoint`` answers 401 to every
tool call it makes.
"""

from contextvars import ContextVar
from dataclasses import dataclass
from enum import StrEnum

from app.api.auth_deps import bearer_token
from app.database import async_session
from app.models.enums import ApiTokenScope, UserRole
from app.services.auth import api_tokens


class Toolset(StrEnum):
    AGENT = "agent"  # task tools (``app/mcp/agent/``), the default
    API = "api"  # one tool per API operation, ``?toolset=api``


@dataclass(frozen=True)
class Caller:
    token: str  # passed on to the API, which checks it again for every tool call
    email: str
    role: UserRole
    scope: ApiTokenScope
    tags: frozenset[str] | None  # ``?tags=people,apps`` on the MCP URL: only these API tools
    toolset: Toolset = Toolset.AGENT

    @property
    def anonymous(self) -> bool:
        return not self.token


current_caller: ContextVar[Caller | None] = ContextVar("mcp_caller", default=None)


def anonymous(tags: str | None, toolset: str | None) -> Caller:
    """Sees the tools an admin with a write token sees; calls none of them."""
    return Caller(
        token="",
        email="",
        role=UserRole.ADMIN,
        scope=ApiTokenScope.WRITE,
        tags=_tags(tags),
        toolset=_toolset(toolset),
    )


async def authenticate(authorization: str | None, tags: str | None, toolset: str | None = None) -> Caller | None:
    token = bearer_token(authorization)
    async with async_session() as session:
        row = await api_tokens.authenticate(session, token)
        if row is None or token is None:
            return None
        await session.commit()  # last_used_at
        return Caller(
            token=token,
            email=row.user.email,
            role=row.user.role,
            scope=row.scope,
            tags=_tags(tags),
            toolset=_toolset(toolset),
        )


def _tags(tags: str | None) -> frozenset[str] | None:
    chosen = frozenset(tag.strip() for tag in tags.split(",") if tag.strip()) if tags else None
    return chosen or None


def _toolset(value: str | None) -> Toolset:
    return Toolset.API if value == Toolset.API else Toolset.AGENT
