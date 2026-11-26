"""Matching accounts to people by e-mail.

Order: manual assignment (never overridden),
primary e-mail, alias. E-mails compare after ``strip()`` and ``lower()``.
Stage 2 sync loads one ``EmailIndex`` per run and calls ``resolve_match``
for every account; single lookups use ``match_email``.
"""

import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from sqlalchemy import select

from app.models import Person, PersonEmail
from app.models.enums import MatchMethod

if TYPE_CHECKING:
    import uuid

    from sqlalchemy.ext.asyncio import AsyncSession

# Domain labels cannot contain dots, so the pattern has one way to match (no polynomial backtracking).
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s.]+(?:\.[^@\s.]+)+$")
MAX_EMAIL_LENGTH = 254


def normalize_email(value: str | None) -> str | None:
    """Strip and lowercase. Empty strings become ``None``."""
    if value is None:
        return None
    normalized = value.strip().lower()
    return normalized or None


def is_valid_email(value: str) -> bool:
    return len(value) <= MAX_EMAIL_LENGTH and bool(_EMAIL_RE.match(value))


@dataclass(frozen=True)
class MatchResult:
    person_id: uuid.UUID | None
    method: MatchMethod


@dataclass
class EmailIndex:
    """Normalized e-mail to person id, separately for primary e-mails and aliases."""

    primary: dict[str, uuid.UUID] = field(default_factory=dict)
    aliases: dict[str, uuid.UUID] = field(default_factory=dict)

    def lookup(self, email: str | None) -> MatchResult:
        normalized = normalize_email(email)
        if normalized is None:
            return MatchResult(None, MatchMethod.NONE)
        if normalized in self.primary:
            return MatchResult(self.primary[normalized], MatchMethod.EMAIL)
        if normalized in self.aliases:
            return MatchResult(self.aliases[normalized], MatchMethod.ALIAS)
        return MatchResult(None, MatchMethod.NONE)


def resolve_match(
    index: EmailIndex,
    email: str | None,
    current_person_id: uuid.UUID | None = None,
    current_method: MatchMethod = MatchMethod.NONE,
) -> MatchResult:
    """Return the owner an account should have.

    A manual assignment (also a manual "nobody") is kept as it is. Otherwise
    the e-mail decides, so an account whose e-mail changed is re-matched.
    """
    if current_method == MatchMethod.MANUAL:
        return MatchResult(current_person_id, MatchMethod.MANUAL)
    return index.lookup(email)


async def load_email_index(session: AsyncSession) -> EmailIndex:
    index = EmailIndex()
    for person_id, email in await session.execute(select(Person.id, Person.primary_email)):
        index.primary[email] = person_id
    for person_id, email in await session.execute(select(PersonEmail.person_id, PersonEmail.email)):
        index.aliases[email] = person_id
    return index


async def match_email(session: AsyncSession, email: str | None) -> MatchResult:
    """Single lookup without loading the whole index."""
    normalized = normalize_email(email)
    if normalized is None:
        return MatchResult(None, MatchMethod.NONE)
    person_id = await session.scalar(select(Person.id).where(Person.primary_email == normalized))
    if person_id is not None:
        return MatchResult(person_id, MatchMethod.EMAIL)
    person_id = await session.scalar(select(PersonEmail.person_id).where(PersonEmail.email == normalized))
    if person_id is not None:
        return MatchResult(person_id, MatchMethod.ALIAS)
    return MatchResult(None, MatchMethod.NONE)


async def email_owner(session: AsyncSession, email: str) -> uuid.UUID | None:
    """Person that already uses ``email`` as primary e-mail or alias."""
    return (await match_email(session, email)).person_id
