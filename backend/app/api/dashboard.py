from fastapi import APIRouter

from app.api.deps import SessionDep
from app.schemas.dashboard import Dashboard
from app.services.dashboard import get_dashboard

router = APIRouter()


@router.get("/dashboard", response_model=Dashboard)
async def read_dashboard(session: SessionDep) -> Dashboard:
    """Overview: counts, monthly cost and alerts (failed syncs, leavers with accounts, pending actions)."""
    return await get_dashboard(session)
