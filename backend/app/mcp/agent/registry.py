"""All task tools, in the order an assistant sees them. A new tool module adds its ``TOOLS`` here."""

import json
from typing import TYPE_CHECKING, Any

import mcp_types as types

from app.mcp.agent import apps, offboarding, people
from app.mcp.agent.base import AgentTool, ToolError

if TYPE_CHECKING:
    from app.mcp.agent.api import AgentApi

AGENT_TOOLS: dict[str, AgentTool] = {tool.name: tool for tool in (*apps.TOOLS, *people.TOOLS, *offboarding.TOOLS)}


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
    clean = {key: value for key, value in result.items() if value is not None}
    return _text(json.dumps(clean, ensure_ascii=False, separators=(",", ":")))


def _text(text: str, error: bool = False) -> types.CallToolResult:
    return types.CallToolResult(content=[types.TextContent(type="text", text=text)], is_error=error)
