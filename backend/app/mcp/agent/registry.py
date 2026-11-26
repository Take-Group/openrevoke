"""All task tools, in the order an assistant sees them. A new tool module adds its ``TOOLS`` here."""

import json
from typing import TYPE_CHECKING, Any

import mcp_types as types
import structlog

from app.mcp.agent import accounts, actions, apps, connections, discovery, me, offboarding, onboarding, people, requests
from app.mcp.agent.base import AgentTool, ToolError

if TYPE_CHECKING:
    from app.mcp.agent.api import AgentApi

log = structlog.get_logger(__name__)

# Listing order: what an admin asks first comes first.
MODULES = (apps, people, offboarding, onboarding, actions, accounts, connections, discovery, requests, me)
AGENT_TOOLS: dict[str, AgentTool] = {tool.name: tool for module in MODULES for tool in module.TOOLS}


async def call(tool: AgentTool, api: AgentApi, arguments: dict[str, Any]) -> types.CallToolResult:
    known = set(tool.input_schema["properties"])
    unknown = set(arguments) - known
    missing = [name for name in tool.input_schema["required"] if arguments.get(name) in (None, "")]
    if unknown or missing:
        problems = [f"unknown: {', '.join(sorted(unknown))}"] * bool(unknown)
        problems += [f"missing: {', '.join(missing)}"] * bool(missing)
        return _text(f"Arguments {'; '.join(problems)}. See the tool's input schema.", error=True)
    try:
        result = await tool.handler(api, arguments)
    except ToolError as error:
        return _text(str(error), error=True)
    except (KeyError, TypeError, ValueError) as error:  # a shape the tool did not expect: a bug, not a crash
        log.exception("mcp_task_tool_failed", tool=tool.name)
        return _text(
            f"Tool {tool.name} failed ({type(error).__name__}: {error}). Report it; try the panel.", error=True
        )
    clean = {key: value for key, value in result.items() if value is not None}
    return _text(json.dumps(clean, ensure_ascii=False, separators=(",", ":")))


def _text(text: str, error: bool = False) -> types.CallToolResult:
    return types.CallToolResult(content=[types.TextContent(type="text", text=text)], is_error=error)
