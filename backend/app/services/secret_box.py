"""Encryption of connector secrets with Fernet and ``OPEN_REVOKE_SECRET_KEY``.

Secrets are stored as one encrypted JSON object per connection
(``connection.secrets_encrypted``). The API never returns them; it shows
only the names of the fields that are set.
"""

import json

from cryptography.fernet import Fernet, InvalidToken

from app.config import settings


class SecretsUnreadableError(Exception):
    """Stored secrets cannot be decrypted, usually because the key changed."""

    def __init__(self) -> None:
        super().__init__(
            "Stored secrets cannot be decrypted. OPEN_REVOKE_SECRET_KEY has probably changed; "
            "enter the secrets of this connection again."
        )


def _fernet() -> Fernet:
    return Fernet(settings.open_revoke_secret_key.get_secret_value().encode())


def encrypt_secrets(values: dict[str, str]) -> bytes | None:
    """Encrypt a dict of secrets. An empty dict means "no secrets" and gives ``None``."""
    if not values:
        return None
    return _fernet().encrypt(json.dumps(values, sort_keys=True).encode())


def decrypt_secrets(token: bytes | None) -> dict[str, str]:
    if not token:
        return {}
    try:
        data = json.loads(_fernet().decrypt(token))
    except (InvalidToken, ValueError) as exc:
        raise SecretsUnreadableError from exc
    if not isinstance(data, dict):
        raise SecretsUnreadableError
    return {str(key): str(value) for key, value in data.items()}


def secret_names(token: bytes | None) -> list[str]:
    """Names of the stored secrets, for the UI. Empty when they cannot be read."""
    try:
        return sorted(decrypt_secrets(token))
    except SecretsUnreadableError:
        return []


def encrypt_value(value: str) -> bytes:
    """Encrypt one secret value (e.g. a temporary password on an action)."""
    return _fernet().encrypt(value.encode())


def decrypt_value(token: bytes) -> str:
    try:
        return _fernet().decrypt(token).decode()
    except InvalidToken as exc:
        raise SecretsUnreadableError from exc
