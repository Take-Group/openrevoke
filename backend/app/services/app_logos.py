"""Logos an admin uploads for an app: checked, stored in ``app.logo``, served to the panel.

PNG, JPEG and WebP are recognised by their first bytes, never by the name or the browser's type.
An SVG is XML that may carry scripts, so it is refused (400) when it has a ``script`` or
``foreignObject`` element, an ``on*`` event attribute, a link (``href``) outside the file, a
``javascript:`` value or a DOCTYPE (entities). Nothing is rewritten: an SVG is stored as uploaded or not
at all. The API also serves every logo with ``nosniff`` and a CSP that blocks scripts
(``api/apps.py``), so a file that slipped through still cannot run code on the panel's origin.
"""

import hashlib
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from typing import TYPE_CHECKING

from sqlalchemy import select

from app.models import App
from app.services import audit
from app.services.errors import InvalidInputError, NotFoundError

if TYPE_CHECKING:
    import uuid

    from sqlalchemy.ext.asyncio import AsyncSession

MAX_BYTES = 256 * 1024
SVG = "image/svg+xml"
_FORBIDDEN_ELEMENTS = {"script", "foreignobject"}
_DOCTYPE = re.compile(rb"<!(DOCTYPE|ENTITY)", re.IGNORECASE)


@dataclass(frozen=True)
class Logo:
    content: bytes
    content_type: str

    @property
    def etag(self) -> str:
        return '"' + hashlib.sha256(self.content).hexdigest()[:32] + '"'


def detect_type(content: bytes) -> str:
    """The image type from the file's first bytes; 400 for anything but PNG, JPEG, WebP or SVG."""
    if content.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if content.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if content[:4] == b"RIFF" and content[8:12] == b"WEBP":
        return "image/webp"
    head = content[:1024].lstrip(b"\xef\xbb\xbf \t\r\n").lower()
    if head.startswith(b"<?xml") or head.startswith(b"<svg") or head.startswith(b"<!--"):
        return SVG
    raise InvalidInputError("The logo must be a PNG, JPEG, WebP or SVG image")


def check_svg(content: bytes) -> None:
    if _DOCTYPE.search(content):
        raise InvalidInputError("SVG logos with a DOCTYPE or entities are not accepted")
    try:
        root = ET.fromstring(content)  # noqa: S314 - no DOCTYPE, so no entities to expand
    except ET.ParseError as exc:
        raise InvalidInputError("The SVG file is not valid XML") from exc
    if _local(root.tag) != "svg":
        raise InvalidInputError("The file is not an SVG image")
    for element in root.iter():
        if _local(element.tag).lower() in _FORBIDDEN_ELEMENTS:
            raise InvalidInputError(f"SVG logos must not contain <{_local(element.tag)}>")
        for name, value in element.attrib.items():
            attribute = _local(name).lower()
            if attribute.startswith("on"):
                raise InvalidInputError(f"SVG logos must not have event attributes ({attribute})")
            if attribute == "href" and not value.strip().startswith("#"):
                raise InvalidInputError("SVG logos must not link outside the file (href)")
            if "javascript:" in value.lower().replace(" ", ""):
                raise InvalidInputError("SVG logos must not contain javascript: values")


def _local(tag: str) -> str:
    """``{http://www.w3.org/2000/svg}svg`` -> ``svg``."""
    return tag.rsplit("}", 1)[-1] if isinstance(tag, str) else ""


async def set_logo(session: AsyncSession, app_id: uuid.UUID, content: bytes) -> None:
    if not content:
        raise InvalidInputError("The file is empty")
    if len(content) > MAX_BYTES:
        raise InvalidInputError(f"The logo is larger than {MAX_BYTES // 1024} KB")
    content_type = detect_type(content)
    if content_type == SVG:
        check_svg(content)
    app = await _get(session, app_id)
    app.logo = content
    app.logo_content_type = content_type
    await session.flush()
    await audit.record(
        session, "app.logo_changed", "app", app.id, {"content_type": content_type, "bytes": len(content)}
    )


async def delete_logo(session: AsyncSession, app_id: uuid.UUID) -> None:
    app = await _get(session, app_id)
    if app.logo_content_type is None:
        return
    app.logo = None
    app.logo_content_type = None
    await session.flush()
    await audit.record(session, "app.logo_removed", "app", app.id, {})


async def get_logo(session: AsyncSession, app_id: uuid.UUID) -> Logo:
    """Loads the deferred ``logo`` column: the only place that reads it."""
    row = (await session.execute(select(App.logo, App.logo_content_type).where(App.id == app_id))).first()
    if row is None or row.logo is None or row.logo_content_type is None:
        raise NotFoundError("The app has no uploaded logo")
    return Logo(content=row.logo, content_type=row.logo_content_type)


async def _get(session: AsyncSession, app_id: uuid.UUID) -> App:
    app = await session.get(App, app_id)
    if app is None:
        raise NotFoundError("App not found")
    return app
