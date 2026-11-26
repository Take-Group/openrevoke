"""Access profiles: named sets of apps with a role in each, assigned to people.

Interface used by access requests: ``auto_approving_profile``. The full service (CRUD,
assignment, onboarding from profiles) is built on top of it.
"""

from typing import TYPE_CHECKING

from sqlalchemy import select

from app.models import AccessProfile, AccessProfileApp, PersonAccessProfile

if TYPE_CHECKING:
    import uuid

    from sqlalchemy.ext.asyncio import AsyncSession


async def auto_approving_profile(
    session: AsyncSession, person_id: uuid.UUID, app_id: uuid.UUID
) -> AccessProfile | None:
    """A profile of the person that holds the app and lets its requests skip the manager step.

    First by name when several do. None: the request follows the app's policy.
    """
    return await session.scalar(
        select(AccessProfile)
        .join(PersonAccessProfile, PersonAccessProfile.profile_id == AccessProfile.id)
        .join(AccessProfileApp, AccessProfileApp.profile_id == AccessProfile.id)
        .where(
            PersonAccessProfile.person_id == person_id,
            AccessProfileApp.app_id == app_id,
            AccessProfile.auto_approve_requests.is_(True),
        )
        .order_by(AccessProfile.name)
        .limit(1)
    )
