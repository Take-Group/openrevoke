"""What a task tool is: a name an assistant understands, its input schema and an async handler.

Task tools answer the questions an admin asks ("what does Anna still have?", "offboard Jan") in
one call. A handler composes the panel's API through ``AgentApi``, so every rule of the panel
still applies, and returns a compact JSON-ready dict instead of a raw API page.
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Literal

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from app.mcp.agent.api import AgentApi

    Handler = Callable[[AgentApi, dict[str, Any]], Awaitable[dict[str, Any]]]


type Audience = Literal["admin", "user"]


class ToolError(Exception):
    """A message for the assistant: what went wrong and what to call instead."""


@dataclass(frozen=True)
class AgentTool:
    name: str
    title: str
    description: str
    input_schema: dict[str, Any]
    handler: Handler
    read_only: bool = True
    destructive: bool = False
    audience: Audience = "admin"  # admin: the company's tools; user: a member's own access and approvals


def schema(properties: dict[str, Any] | None = None, required: tuple[str, ...] = ()) -> dict[str, Any]:
    return {
        "type": "object",
        "properties": properties or {},
        "required": list(required),
        "additionalProperties": False,
    }


PERSON_ARG = {
    "type": "string",
    "description": (
        "The person: e-mail, full name or id. A name that matches several people returns them to choose from."
    ),
}
APP_ARG = {
    "type": "string",
    "description": 'The app: name ("Slack"), slug or id.',
}
