import uuid
from typing import Annotated

from fastapi import APIRouter, File, Query, UploadFile

from app.api.deps import SessionDep
from app.schemas.accounts import AccountImportResult, AccountOut, AccountUpdate
from app.services import accounts, accounts_import

router = APIRouter(prefix="/accounts")


@router.post("/import", response_model=AccountImportResult)
async def import_accounts(
    session: SessionDep,
    file: Annotated[UploadFile, File(description="CSV: app,email,username,display_name,role,status,kind")],
    dry_run: Annotated[bool, Query(description="Preview the changes without saving")] = False,
    create_apps: Annotated[bool, Query(description="Create apps the file names but Open Revoke lacks")] = False,
) -> AccountImportResult:
    """Adds or updates accounts of apps without a connector from a CSV (several apps in one file).

    Header ``app,email,username,display_name,role,status,kind``; ``app`` and one of email, username,
    display_name are required. Nothing is deleted. Try ``dry_run=true`` first.
    """
    # Read one byte past the limit: enough to refuse a too large file without loading all of it.
    content = await file.read(accounts_import.MAX_BYTES + 1)
    return await accounts_import.import_csv(session, content, dry_run=dry_run, create_apps=create_apps)


@router.patch("/{account_id}", response_model=AccountOut)
async def update_account(account_id: uuid.UUID, data: AccountUpdate, session: SessionDep) -> AccountOut:
    """Assigns an account to a person (``person_id``, manual: sync keeps it) or changes its kind.

    Only the fields present change; ``role``, ``status`` and ``display_name`` only without a connection.
    """
    return await accounts.update_account(session, account_id, data, data.model_fields_set)
