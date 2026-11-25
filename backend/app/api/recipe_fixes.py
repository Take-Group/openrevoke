import uuid

from fastapi import APIRouter

from app.api.deps import SessionDep
from app.schemas.recipe_fixes import RecipeFixList, RecipeFixOut
from app.services import recipe_fixes

router = APIRouter(prefix="/recipe-fixes")


@router.get("", response_model=RecipeFixList)
async def list_recipe_fixes(session: SessionDep, recipe_app: str | None = None) -> RecipeFixList:
    """Local fixes of click recipe steps, newest first; ``recipe_app`` is a connector key."""
    items = await recipe_fixes.list_fixes(session, recipe_app=recipe_app)
    return RecipeFixList(items=items, total=len(items))


@router.post("/{fix_id}/approve", response_model=RecipeFixOut)
async def approve_recipe_fix(fix_id: uuid.UUID, session: SessionDep) -> RecipeFixOut:
    """A proposed fix (irreversible click) becomes active; retry the action to use it."""
    return await recipe_fixes.approve(session, fix_id)


@router.post("/{fix_id}/reject", response_model=RecipeFixOut)
async def reject_recipe_fix(fix_id: uuid.UUID, session: SessionDep) -> RecipeFixOut:
    """Rejects a proposal or reverts an active fix: runs go back to the recipe's own locators."""
    return await recipe_fixes.reject(session, fix_id)
