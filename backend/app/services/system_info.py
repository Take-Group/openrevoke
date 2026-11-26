"""What the admin sees about this installation: its version and whether a newer release exists."""

from app.config import settings
from app.schemas.system import SystemVersion
from app.services import update_check


async def version_overview() -> SystemVersion:
    latest = await update_check.stored() if update_check.enabled() else None
    return SystemVersion(
        version=settings.version,
        install_method=settings.install_method,
        update_check=update_check.enabled(),
        latest_version=latest.version if latest else None,
        latest_url=latest.url if latest else None,
        latest_published_at=latest.published_at if latest else None,
        checked_at=latest.checked_at if latest else None,
        update_available=bool(latest and update_check.is_newer(latest.version, settings.version)),
        security_update=bool(latest and latest.security and update_check.is_newer(latest.version, settings.version)),
    )
