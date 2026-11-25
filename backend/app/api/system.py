"""This installation: version and update notice (admins only, mounted in ``domain_router``)."""

from fastapi import APIRouter

from app.schemas.system import SystemVersion
from app.services import system_info

router = APIRouter(prefix="/system", tags=["system"])


@router.get("/version", response_model=SystemVersion)
async def get_system_version() -> SystemVersion:
    """Running version and the newest stable release from the hourly check, for the panel's update notice."""
    return await system_info.version_overview()
