from fastapi import APIRouter

from app.api.deps import SessionDep
from app.schemas.dashboard import Dashboard
from app.services.dashboard import get_dashboard

router = APIRouter()


@router.get("/dashboard", response_model=Dashboard)
async def read_dashboard(session: SessionDep) -> Dashboard:
    return await get_dashboard(session)
