"""State the host command `open-revoke` asks before an update."""

from typing import TYPE_CHECKING

from sqlalchemy import func, select

from app.models import Action
from app.models.enums import ActionStatus

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

# Approved actions wait for their connection lock inside a running workflow, so they count too.
IN_FLIGHT = (ActionStatus.APPROVED, ActionStatus.RUNNING, ActionStatus.VERIFYING)


async def actions_in_flight(session: AsyncSession) -> int:
    """Write actions whose Temporal workflow may still be running."""
    query = select(func.count()).select_from(Action).where(Action.status.in_(IN_FLIGHT))
    return int(await session.scalar(query) or 0)
