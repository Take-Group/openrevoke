"""Settings of the encryption key (config.py)."""

from typing import TYPE_CHECKING

import pytest
from cryptography.fernet import Fernet
from pydantic import ValidationError

from app.config import Settings

if TYPE_CHECKING:
    from pathlib import Path


def test_key_from_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    key = Fernet.generate_key().decode()
    path = tmp_path / "key"
    path.write_text(key + "\n")
    monkeypatch.delenv("OPEN_REVOKE_SECRET_KEY", raising=False)
    monkeypatch.setenv("OPEN_REVOKE_SECRET_KEY_FILE", str(path))
    assert Settings(_env_file=None).open_revoke_secret_key.get_secret_value() == key


def test_previous_keys_are_listed(monkeypatch: pytest.MonkeyPatch) -> None:
    first, second = Fernet.generate_key().decode(), Fernet.generate_key().decode()
    monkeypatch.setenv("OPEN_REVOKE_SECRET_KEY_PREVIOUS", f"{first}, {second}")
    assert Settings(_env_file=None).previous_secret_keys == [first, second]


@pytest.mark.parametrize("variable", ["OPEN_REVOKE_SECRET_KEY", "OPEN_REVOKE_SECRET_KEY_PREVIOUS"])
def test_invalid_keys_are_refused(variable: str, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(variable, "not-a-fernet-key")
    with pytest.raises(ValidationError):
        Settings(_env_file=None)
