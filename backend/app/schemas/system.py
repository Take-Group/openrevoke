from pydantic import Field

from app.schemas.common import ApiModel


class SystemVersion(ApiModel):
    version: str = Field(description="Version of this installation; `dev` in the local stack")
    update_check: bool = Field(description="The hourly check for a newer release is on (OPEN_REVOKE_UPDATE_CHECK)")
    latest_version: str | None = Field(description="Newest stable release seen by the last check; null before one")
    latest_url: str | None = Field(description="Release notes of that release")
    latest_published_at: str | None
    checked_at: str | None = Field(description="When the last successful check ran (ISO 8601)")
    update_available: bool = Field(description="latest_version is newer than version")
    security_update: bool = Field(description="The newer release has a Security section in its notes")
