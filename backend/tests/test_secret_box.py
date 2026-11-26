"""Encryption of stored secrets and key rotation (services/secret_box.py)."""

import pytest
from cryptography.fernet import Fernet
from pydantic import SecretStr

from app.config import settings
from app.services import secret_box


@pytest.fixture
def keys(monkeypatch: pytest.MonkeyPatch) -> tuple[str, str]:
    old, new = Fernet.generate_key().decode(), Fernet.generate_key().decode()
    monkeypatch.setattr(settings, "open_revoke_secret_key", SecretStr(old))
    monkeypatch.setattr(settings, "open_revoke_secret_key_previous", SecretStr(""))
    return old, new


def _use(monkeypatch: pytest.MonkeyPatch, current: str, previous: str = "") -> None:
    monkeypatch.setattr(settings, "open_revoke_secret_key", SecretStr(current))
    monkeypatch.setattr(settings, "open_revoke_secret_key_previous", SecretStr(previous))


def test_round_trip(keys: tuple[str, str]) -> None:
    token = secret_box.encrypt_secrets({"api_token": "t0ken", "url": "https://example.com"})
    assert token is not None
    assert b"t0ken" not in token
    assert secret_box.decrypt_secrets(token) == {"api_token": "t0ken", "url": "https://example.com"}
    assert secret_box.encrypt_secrets({}) is None
    assert secret_box.decrypt_secrets(None) == {}


def test_wrong_key_is_unreadable(keys: tuple[str, str], monkeypatch: pytest.MonkeyPatch) -> None:
    token = secret_box.encrypt_value("secret")
    _use(monkeypatch, keys[1])
    with pytest.raises(secret_box.SecretsUnreadableError):
        secret_box.decrypt_value(token)
    assert secret_box.secret_names(token) == []


def test_rotation(keys: tuple[str, str], monkeypatch: pytest.MonkeyPatch) -> None:
    old, new = keys
    token = secret_box.encrypt_value("secret")
    # During a rotation the previous key still decrypts, the new one encrypts.
    _use(monkeypatch, new, old)
    assert secret_box.decrypt_value(token) == "secret"
    rotated = secret_box.rotate_token(token)
    # After the rotation the new key alone reads it, the old key alone does not.
    _use(monkeypatch, new)
    assert secret_box.decrypt_value(rotated) == "secret"
    _use(monkeypatch, old)
    with pytest.raises(secret_box.SecretsUnreadableError):
        secret_box.decrypt_value(rotated)
