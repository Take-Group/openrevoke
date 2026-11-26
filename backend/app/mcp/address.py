"""Where the MCP server listens: on the panel's origin, so self-hosting needs no extra port."""

from app.config import settings

MCP_PATH = "/mcp"


def mcp_url() -> str:
    return f"{settings.public_url.rstrip('/')}{MCP_PATH}"
