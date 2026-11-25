"""Password hashing (Argon2id) and the password policy."""

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

from app.services.errors import InvalidInputError

MIN_LENGTH = 12
MAX_LENGTH = 128

_hasher = PasswordHasher()
# Verified when the e-mail is unknown, so a wrong e-mail takes as long as a wrong password.
_DUMMY_HASH = _hasher.hash("open-revoke-dummy-password")


def check_policy(password: str) -> None:
    if len(password) < MIN_LENGTH:
        raise InvalidInputError(f"The password must have at least {MIN_LENGTH} characters.")
    if len(password) > MAX_LENGTH:
        raise InvalidInputError(f"The password can have at most {MAX_LENGTH} characters.")
    if password.strip() != password or not password.strip():
        raise InvalidInputError("The password cannot start or end with a space.")


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password_hash: str | None, password: str) -> bool:
    try:
        return _hasher.verify(password_hash or _DUMMY_HASH, password) and password_hash is not None
    except VerificationError, InvalidHashError:
        return False
