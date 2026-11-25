import uuid
from datetime import datetime

from pydantic import Field

from app.models.enums import ApiTokenScope
from app.schemas.common import ApiModel


class ApiTokenOut(ApiModel):
    id: uuid.UUID
    name: str
    prefix: str = Field(description="First characters of the token, to tell tokens apart")
    scope: ApiTokenScope
    created_at: datetime
    last_used_at: datetime | None


class ApiTokenList(ApiModel):
    items: list[ApiTokenOut]
    mcp_url: str = Field(description="Address of the MCP server for AI assistants (Claude Code, Codex, Cursor)")


class ApiTokenCreate(ApiModel):
    name: str = Field(min_length=1, max_length=100, description="Where the token is used, e.g. 'Claude Code'")
    scope: ApiTokenScope = Field(description="read: GET requests only; write: everything the owner's role allows")


class ApiTokenCreated(ApiModel):
    token: ApiTokenOut
    secret: str = Field(description="The token itself. Shown once: copy it now")
    mcp_url: str
