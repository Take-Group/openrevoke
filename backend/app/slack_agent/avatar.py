"""The default icon of the Slack app (512-2000 px square, Slack's limits for ``apps.icon.set``)."""

from pathlib import Path

DEFAULT_AVATAR = Path(__file__).parent / "assets" / "avatar.png"
MAX_BYTES = 5 * 1024 * 1024
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
JPEG_SIGNATURE = b"\xff\xd8\xff"


def default_avatar() -> bytes:
    return DEFAULT_AVATAR.read_bytes()


def image_type(data: bytes) -> str | None:
    """``image/png`` or ``image/jpeg`` from the first bytes; ``None`` for anything else."""
    if data.startswith(PNG_SIGNATURE):
        return "image/png"
    if data.startswith(JPEG_SIGNATURE):
        return "image/jpeg"
    return None
