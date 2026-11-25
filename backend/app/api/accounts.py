import uuid

from fastapi import APIRouter

from app.api.deps import SessionDep
from app.schemas.accounts import AccountOut, AccountUpdate
from app.services import accounts

router = APIRouter(prefix="/accounts")


@router.patch("/{account_id}", response_model=AccountOut)
async def update_account(account_id: uuid.UUID, data: AccountUpdate, session: SessionDep) -> AccountOut:
    """Assigns an account to a person (``person_id``, manual: sync keeps it) or changes its kind.

    Only the fields present change; ``role``, ``status`` and ``display_name`` only without a connection.
    """
    return await accounts.update_account(session, account_id, data, data.model_fields_set)
