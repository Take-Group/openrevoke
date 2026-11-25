from contextlib import asynccontextmanager
from typing import TYPE_CHECKING

import structlog
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.errors import register_error_handlers
from app.api.host_check import AllowedHostsMiddleware
from app.api.router import api_router
from app.browser.provider import get_browser_provider
from app.config import settings
from app.database import async_session, engine
from app.logging import setup_logging
from app.mcp.address import MCP_PATH
from app.mcp.server import McpEndpoint, OpenRevokeMcp
from app.redis import redis_client
from app.services.auth import setup_link, sign_in

if TYPE_CHECKING:
    from fastapi.routing import APIRoute

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging(debug=settings.debug)
    logger.info("Starting application", app_name=settings.app_name, version=settings.version)
    await _announce_setup_link()
    async with mcp.run():
        yield
    await get_browser_provider().disconnect()  # drops the CDP connection; Chromium keeps running
    await redis_client.aclose()
    await engine.dispose()
    logger.info("Application shutdown complete")


async def _announce_setup_link() -> None:
    """A fresh instance prints its setup link; without a database yet it says nothing (the gate shows an error)."""
    try:
        async with async_session() as session:
            if await sign_in.setup_required(session):
                await setup_link.announce()
    except Exception:
        logger.exception("Could not prepare the setup link; run `python -m app.cli setup-link`")


def _operation_id(route: APIRoute) -> str:
    """Operation id = endpoint function name, e.g. ``list_people``. Clean names for generated clients."""
    return route.name


app = FastAPI(
    title=settings.app_name,
    version=settings.version,
    debug=settings.debug,
    lifespan=lifespan,
    generate_unique_id_function=_operation_id,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.trusted_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(AllowedHostsMiddleware, allowed_hosts=settings.trusted_hosts)
register_error_handlers(app)
app.include_router(api_router)

# MCP server for AI assistants (skills/backend/mcp.md): every API operation a token reaches is a tool.
mcp = OpenRevokeMcp(app)
app.add_route(MCP_PATH, McpEndpoint(mcp), methods=["GET", "POST", "DELETE"], include_in_schema=False)


def run() -> None:
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
    )
