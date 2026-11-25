"""Is there a newer stable release? Asked hourly by ``CheckForUpdateWorkflow``.

``GET {OPEN_REVOKE_UPDATE_URL}`` (GitHub's "latest release": the newest one that is neither a
draft nor a pre-release). Nothing about the installation is sent beyond what any HTTP server
sees. GitHub allows 60 unauthenticated requests an hour per IP; one an hour is enough.
The answer is kept in Redis; it is refetched within an hour after a Redis restart.
skills/backend/releases.md.
"""

import json
import re
from dataclasses import asdict, dataclass
from datetime import UTC, datetime

import httpx
import structlog

from app.config import settings
from app.redis import redis_client

logger = structlog.get_logger()

KEY = "open-revoke:update-check"
TIMEOUT_SECONDS = 15
# A "Security" heading in the release notes (CHANGELOG.md section) makes the panel notice stronger.
SECURITY_HEADING = re.compile(r"^#{1,6}\s*security\b", re.IGNORECASE | re.MULTILINE)
VERSION = re.compile(r"^v?(\d+)\.(\d+)\.(\d+)(?:-([0-9A-Za-z.-]+))?$")


@dataclass(frozen=True)
class LatestRelease:
    version: str
    url: str
    published_at: str | None
    security: bool
    checked_at: str


def parse_version(value: str) -> tuple[int, int, int, bool] | None:
    """``(major, minor, patch, is_final)``; None for anything that is not SemVer (e.g. ``dev``)."""
    match = VERSION.match(value.strip())
    if match is None:
        return None
    major, minor, patch, prerelease = match.groups()
    return int(major), int(minor), int(patch), prerelease is None


def is_newer(candidate: str, current: str) -> bool:
    new, old = parse_version(candidate), parse_version(current)
    if new is None or old is None:
        return False
    # A final release sorts after its own pre-releases: 0.5.0 > 0.5.0-rc.1.
    return new > old


def enabled() -> bool:
    """Off by setting, and for builds without a release number (the local stack runs ``dev``)."""
    return settings.update_check and parse_version(settings.version) is not None


async def fetch() -> LatestRelease | None:
    """The latest stable release, or None when there is none yet (404) or the check failed."""
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": f"open-revoke/{settings.version}",
    }
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT_SECONDS, follow_redirects=True) as client:
            response = await client.get(settings.update_check_url, headers=headers)
    except httpx.HTTPError as exc:
        logger.info("update_check_unreachable", error=str(exc))
        return None
    if response.status_code != 200:
        # 404: no release or no public repository yet; 403: rate limit. Both mean "no news", not an error.
        logger.info("update_check_no_answer", status=response.status_code)
        return None
    data = response.json()
    tag = str(data.get("tag_name") or "")
    if parse_version(tag) is None:
        logger.info("update_check_not_semver", tag=tag)
        return None
    return LatestRelease(
        version=tag.removeprefix("v"),
        url=str(data.get("html_url") or ""),
        published_at=data.get("published_at"),
        security=bool(SECURITY_HEADING.search(str(data.get("body") or ""))),
        checked_at=datetime.now(UTC).isoformat(),
    )


async def check() -> str:
    """Fetch and store the latest release. Returns a short summary for the workflow history."""
    if not enabled():
        return "update check off"
    latest = await fetch()
    if latest is None:
        return "no release information"
    await redis_client.set(KEY, json.dumps(asdict(latest)))
    newer = is_newer(latest.version, settings.version)
    return f"latest {latest.version}, running {settings.version}" + (" (update available)" if newer else "")


async def stored() -> LatestRelease | None:
    raw = await redis_client.get(KEY)
    if not raw:
        return None
    try:
        return LatestRelease(**json.loads(raw))
    except TypeError, ValueError:
        return None
