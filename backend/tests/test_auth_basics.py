"""Passwords, TOTP, client address and CSV cells: the pure parts of sign-in and exports."""

import pyotp
import pytest
from starlette.requests import Request

from app.api.client_ip import client_ip
from app.services.auth import passwords, totp
from app.services.csv_cells import safe_cell
from app.services.errors import InvalidInputError


def test_password_hash_is_argon2id() -> None:
    hashed = passwords.hash_password("correct horse battery")
    assert hashed.startswith("$argon2id$")
    assert passwords.verify_password(hashed, "correct horse battery")
    assert not passwords.verify_password(hashed, "wrong horse battery")
    assert not passwords.verify_password(None, "correct horse battery")


@pytest.mark.parametrize("password", ["short", " leading-space-pass", "x" * 129])
def test_password_policy(password: str) -> None:
    with pytest.raises(InvalidInputError):
        passwords.check_policy(password)


def test_totp_code_is_used_once() -> None:
    secret = totp.new_secret()
    now = 1_800_000_000.0
    code = pyotp.TOTP(secret).at(now)
    step = totp.matching_step(secret, code, after_step=None, now=now)
    assert step is not None
    assert totp.matching_step(secret, code, after_step=step, now=now) is None
    assert totp.matching_step(secret, "12345", after_step=None, now=now) is None


def _request(headers: dict[str, str], peer: str = "10.0.0.9") -> Request:
    raw = [(name.lower().encode(), value.encode()) for name, value in headers.items()]
    return Request({"type": "http", "headers": raw, "client": (peer, 1234)})


def test_client_ip_takes_the_last_forwarded_entry() -> None:
    assert client_ip(_request({"X-Forwarded-For": "1.2.3.4, 203.0.113.7"})) == "203.0.113.7"
    assert client_ip(_request({})) == "10.0.0.9"


@pytest.mark.parametrize("value", ["=1+1", "+cmd", "-2", "@SUM(A1)", "\t=1"])
def test_csv_cells_cannot_start_a_formula(value: str) -> None:
    assert safe_cell(value).startswith("'")
    assert safe_cell("plain") == "plain"
    assert safe_cell(None) == ""
