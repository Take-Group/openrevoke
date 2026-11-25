"""TOTP codes (RFC 6238) as in Google Authenticator: 6 digits, 30 s, SHA-1."""

import time
from dataclasses import dataclass

import pyotp
import segno

from app.config import settings

# A code from the previous or the next 30 s window is accepted too (clock drift).
VALID_WINDOW = 1


@dataclass(frozen=True)
class Enrollment:
    secret: str
    otpauth_uri: str
    qr_svg: str  # data: URI with an SVG image of the QR code


def new_secret() -> str:
    return pyotp.random_base32()


def enrollment(secret: str, email: str) -> Enrollment:
    uri = pyotp.TOTP(secret).provisioning_uri(name=email, issuer_name=settings.app_name)
    qr = segno.make(uri, error="m").svg_data_uri(scale=5, border=2)
    return Enrollment(secret=secret, otpauth_uri=uri, qr_svg=qr)


def matching_step(secret: str, code: str, *, after_step: int | None, now: float | None = None) -> int | None:
    """Time step the code belongs to, or None. Steps up to ``after_step`` are refused (used before)."""
    code = code.strip().replace(" ", "")
    if len(code) != 6 or not code.isdigit():
        return None
    totp = pyotp.TOTP(secret)
    current = int((time.time() if now is None else now) // totp.interval)
    for step in range(current - VALID_WINDOW, current + VALID_WINDOW + 1):
        if after_step is not None and step <= after_step:
            continue
        if pyotp.utils.strings_equal(totp.at(step * totp.interval), code):
            return step
    return None
