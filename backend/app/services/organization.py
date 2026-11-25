"""The organization row (id = 1): name, currency, time zone and the self sign-up rules."""

from typing import TYPE_CHECKING, Any

from app.models import Organization
from app.services import audit
from app.services.errors import InvalidInputError, NotFoundError

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


async def get(session: AsyncSession) -> Organization:
    organization = await session.get(Organization, 1)
    if organization is None:
        raise NotFoundError("The organization is not set up yet.")
    return organization


async def update(session: AsyncSession, changes: dict[str, Any]) -> Organization:
    """Apply the fields sent by the admin. Auto-approval needs at least one domain, or it would let nobody in."""
    organization = await get(session)
    for name, value in changes.items():
        setattr(organization, name, value)
    if organization.registration_auto_approve and not organization.registration_domains:
        raise InvalidInputError("Add at least one e-mail domain for automatic approval, e.g. example.com.")
    if changes:
        await audit.record(session, "organization.updated", "organization", None, changes)
    return organization
