"""``/api/me``: the signed-in user's own access. The only panel API a ``user`` (not admin) can call."""

from fastapi import APIRouter, status

from app.api.auth_deps import CurrentUserDep
from app.api.deps import ActionDispatcherDep, SessionDep
from app.schemas.me import MyAccess, MyAccessRequestCreate, MyAccessRequestResult
from app.services import my_access

router = APIRouter(prefix="/me")


@router.get("/access", response_model=MyAccess)
async def get_my_access(session: SessionDep, user: CurrentUserDep) -> MyAccess:
    """The signed-in user's own accounts, open requests and the apps they can ask for."""
    return await my_access.overview(session, user)


@router.post("/access-requests", response_model=MyAccessRequestResult, status_code=status.HTTP_201_CREATED)
async def request_my_access(
    data: MyAccessRequestCreate, session: SessionDep, user: CurrentUserDep, dispatcher: ActionDispatcherDep
) -> MyAccessRequestResult:
    """Ask for an account in an app. The app's self-service policy decides if an admin approves it first."""
    return await my_access.request(session, user, app_id=data.app_id, message=data.message, dispatcher=dispatcher)
