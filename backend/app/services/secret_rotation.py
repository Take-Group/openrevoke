"""Re-encryption of every stored secret with the current ``OPEN_REVOKE_SECRET_KEY``.

Step of a key rotation (``open-revoke rotate-key`` on the host, ``python -m app.cli
rotate-secrets`` in the image): the new key is ``OPEN_REVOKE_SECRET_KEY``, the old one is
in ``OPEN_REVOKE_SECRET_KEY_PREVIOUS``. Afterwards the old key decrypts nothing stored in
the database. Short-lived encrypted values in Redis (sign-in tickets, Google OAuth state)
expire within minutes and are not rotated.

A new encrypted column must be added to ``ENCRYPTED_COLUMNS``.
"""

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from sqlalchemy import select, update

from app.models import Action, AiSettings, Connection, SlackAgent, User
from app.services import audit
from app.services.secret_box import SecretsUnreadableError, rotate_token

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession
    from sqlalchemy.orm import InstrumentedAttribute

ENCRYPTED_COLUMNS: list[tuple[type[Any], str]] = [
    (Connection, "secrets_encrypted"),
    (User, "totp_secret_encrypted"),
    (AiSettings, "api_key_encrypted"),
    (Action, "secret_result_encrypted"),
    (SlackAgent, "secrets_encrypted"),
]


@dataclass
class RotationResult:
    rotated: dict[str, int] = field(default_factory=dict)
    # Values no configured key can decrypt: left as they are, their owners enter them again.
    unreadable: dict[str, list[str]] = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return not self.unreadable


async def rotate_stored_secrets(session: AsyncSession) -> RotationResult:
    result = RotationResult()
    for model, column_name in ENCRYPTED_COLUMNS:
        column: InstrumentedAttribute[bytes | None] = getattr(model, column_name)
        label = f"{model.__tablename__}.{column_name}"
        rows = (await session.execute(select(model.id, column).where(column.is_not(None)))).all()
        count = 0
        for row_id, token in rows:
            try:
                new_token = rotate_token(token)
            except SecretsUnreadableError:
                result.unreadable.setdefault(label, []).append(str(row_id))
                continue
            await session.execute(update(model).where(model.id == row_id).values({column_name: new_token}))
            count += 1
        result.rotated[label] = count
    await audit.record(
        session,
        "secrets.rotated",
        "organization",
        None,
        {"rotated": result.rotated, "unreadable": {k: len(v) for k, v in result.unreadable.items()}},
    )
    return result
