"""Local fixes of click recipe steps: read for a run, listed, approved, rejected (docs/browser-recipes.md).

An AI repair of an ordinary step is stored ``active`` and used at once; a fix
of an irreversible click or of a removal step is ``proposed`` and no run uses it until an admin
approves it. Rejecting an active fix reverts it: runs go back to the repo's
candidates. Rows are never deleted, so the history stays.
"""

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import select

from app.models import RecipeFix
from app.models.enums import RecipeFixStatus
from app.recipes.repair import Alternative
from app.schemas.recipe_fixes import RecipeFixOut
from app.services import audit
from app.services.errors import ConflictError, NotFoundError

if TYPE_CHECKING:
    import uuid

    from sqlalchemy.ext.asyncio import AsyncSession

F = RecipeFixStatus


async def active_fixes(session: AsyncSession, recipe_app: str, recipe_action: str) -> dict[str, list[Alternative]]:
    """Active fixes per step id, newest first (the newest is tried first)."""
    rows = await session.scalars(
        select(RecipeFix)
        .where(
            RecipeFix.recipe_app == recipe_app,
            RecipeFix.recipe_action == recipe_action,
            RecipeFix.status == F.ACTIVE,
        )
        .order_by(RecipeFix.created_at.desc())
    )
    fixes: dict[str, list[Alternative]] = {}
    for row in rows:
        fixes.setdefault(row.step_id, []).append(alternative_of(row))
    return fixes


async def list_fixes(
    session: AsyncSession, *, recipe_app: str | None = None, action_ids: list[uuid.UUID] | None = None
) -> list[RecipeFixOut]:
    query = select(RecipeFix).order_by(RecipeFix.created_at.desc())
    if recipe_app:
        query = query.where(RecipeFix.recipe_app == recipe_app)
    if action_ids is not None:
        if not action_ids:
            return []
        query = query.where(RecipeFix.action_id.in_(action_ids))
    return [fix_out(row) for row in await session.scalars(query)]


async def approve(session: AsyncSession, fix_id: uuid.UUID) -> RecipeFixOut:
    """A proposed fix becomes active: the next run (a retry of the action) uses it."""
    fix = await _get(session, fix_id)
    if fix.status != F.PROPOSED:
        raise ConflictError(f"Only a proposed fix can be approved (this one is {fix.status})")
    return await _decide(session, fix, F.ACTIVE, "recipe_fix.approved")


async def reject(session: AsyncSession, fix_id: uuid.UUID) -> RecipeFixOut:
    """Reject a proposal or revert an active fix."""
    fix = await _get(session, fix_id)
    if fix.status == F.REJECTED:
        raise ConflictError("The fix is already rejected")
    return await _decide(session, fix, F.REJECTED, "recipe_fix.rejected")


def alternative_of(row: RecipeFix) -> Alternative:
    return Alternative.model_validate({"within": row.within, "target": row.target})


def fix_out(row: RecipeFix) -> RecipeFixOut:
    return RecipeFixOut(
        id=row.id,
        recipe_app=row.recipe_app,
        recipe_action=row.recipe_action,
        step_id=row.step_id,
        step_goal=row.step_goal,
        irreversible=row.irreversible,
        locator=alternative_of(row).describe(),
        status=row.status,
        author=row.author,
        note=row.note,
        action_id=row.action_id,
        created_at=row.created_at,
        decided_at=row.decided_at,
    )


async def _get(session: AsyncSession, fix_id: uuid.UUID) -> RecipeFix:
    fix = await session.get(RecipeFix, fix_id, with_for_update=True, populate_existing=True)
    if fix is None:
        raise NotFoundError("Recipe fix not found")
    return fix


async def _decide(session: AsyncSession, fix: RecipeFix, status: RecipeFixStatus, event: str) -> RecipeFixOut:
    previous = fix.status
    fix.status = status
    fix.decided_at = datetime.now(UTC)
    await session.flush()
    await audit.record(
        session,
        event,
        "recipe_fix",
        fix.id,
        {"recipe": f"{fix.recipe_app}/{fix.recipe_action}", "step_id": fix.step_id, "previous": str(previous)},
    )
    return fix_out(fix)
