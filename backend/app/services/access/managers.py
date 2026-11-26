"""A person's manager and the panel user who can decide for them.

Used by access requests (the manager step) and by the people pages. The manager is
``person.manager_id``; the manager decides in the panel when an active panel user has their
primary e-mail or one of their aliases.
"""

from typing import TYPE_CHECKING

from sqlalchemy import select

from app.models import Person, PersonEmail, User
from app.models.enums import PersonStatus, UserStatus

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


async def manager_of(session: AsyncSession, person: Person) -> Person | None:
    """The person's manager, or None when not set."""
    if person.manager_id is None:
        return None
    return await session.get(Person, person.manager_id)


async def emails_of(session: AsyncSession, person: Person) -> list[str]:
    """Primary e-mail first, then the aliases (all lower case)."""
    aliases = await session.scalars(
        select(PersonEmail.email).where(PersonEmail.person_id == person.id).order_by(PersonEmail.email)
    )
    return [person.primary_email, *aliases]


async def panel_user_of(session: AsyncSession, person: Person) -> User | None:
    """The active panel user of a person, matched by primary e-mail, then by alias."""
    emails = await emails_of(session, person)
    users = {
        user.email: user
        for user in await session.scalars(select(User).where(User.email.in_(emails), User.status == UserStatus.ACTIVE))
    }
    return next((users[email] for email in emails if email in users), None)


async def manager_panel_user(session: AsyncSession, person: Person) -> User | None:
    """The panel user who decides as the person's manager; None when there is no such manager.

    No manager, a manager who left, or a manager without an active panel account all give None.
    The caller decides the fallback (Slack identity, then an admin).
    """
    manager = await manager_of(session, person)
    if manager is None or manager.status == PersonStatus.LEFT:
        return None
    return await panel_user_of(session, manager)
