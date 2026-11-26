import uuid
from typing import Annotated

from fastapi import APIRouter, File, Query, Response, UploadFile, status

from app.api.deps import SessionDep
from app.api.params import DEFAULT_LIMIT, Limit, Offset, SearchQuery
from app.models.enums import PersonKind, PersonStatus
from app.schemas.actions import OffboardResult, OnboardRequest, OnboardResult
from app.schemas.people import PersonCreate, PersonDetail, PersonPage, PersonUpdate
from app.schemas.people_import import ImportResult
from app.services import offboarding, onboarding, people, people_import

router = APIRouter(prefix="/people")


@router.get("", response_model=PersonPage)
async def list_people(
    session: SessionDep,
    q: SearchQuery = None,
    status: PersonStatus | None = None,
    kind: PersonKind | None = None,
    no_manager: Annotated[bool, Query(description="Only people with no manager set")] = False,
    limit: Limit = DEFAULT_LIMIT,
    offset: Offset = 0,
) -> PersonPage:
    """``q`` also matches department and job title.

    ``kind_counts`` counts the matches of ``q``, ``status`` and ``no_manager`` per kind, for the filter tabs.
    """
    items, total, kind_counts = await people.list_people(
        session, q=q, status=status, kind=kind, limit=limit, offset=offset, no_manager=no_manager
    )
    return PersonPage(items=items, total=total, kind_counts=kind_counts)


@router.post("", response_model=PersonDetail, status_code=status.HTTP_201_CREATED)
async def create_person(data: PersonCreate, session: SessionDep) -> PersonDetail:
    """Adds a person by hand. Accounts with their e-mail or aliases are matched to them."""
    return await people.create_person(session, data)


@router.post("/import", response_model=ImportResult)
async def import_people(
    session: SessionDep,
    file: Annotated[UploadFile, File(description=f"CSV: {people_import.HEADER}")],
    dry_run: Annotated[bool, Query(description="Preview the changes without saving")] = False,
) -> ImportResult:
    """Adds or updates people from a CSV (header: email,first_name,last_name,employee_code,aliases,
    manager_email,department,job_title; only email is required).

    ``manager_email`` must be a person already stored or a row of the same file; it is set as manual,
    so syncs keep it. Try ``dry_run=true`` first.
    """
    # Read one byte past the limit: enough to refuse a too large file without loading all of it.
    content = await file.read(people_import.MAX_BYTES + 1)
    return await people_import.import_people(session, content, dry_run=dry_run)


@router.get("/{person_id}", response_model=PersonDetail)
async def get_person(person_id: uuid.UUID, session: SessionDep) -> PersonDetail:
    """One person with their e-mails, sources, accounts in every app, monthly cost, manager and reports."""
    return await people.get_person(session, person_id)


@router.patch("/{person_id}", response_model=PersonDetail)
async def update_person(person_id: uuid.UUID, data: PersonUpdate, session: SessionDep) -> PersonDetail:
    """Changes a person's name, e-mails, code, kind, notes, manager, department or job title.

    Only the fields present change. ``manager_id`` is kept by syncs (manual); null clears it. 400 when the
    manager is the person, has left, is a service account, or reports to the person (a loop).
    """
    return await people.update_person(session, person_id, data, data.model_fields_set)


@router.delete("/{person_id}", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
async def delete_person(person_id: uuid.UUID, session: SessionDep) -> Response:
    """Deletes a person without accounts and actions (409 otherwise), e.g. one added by mistake."""
    await people.delete_person(session, person_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{person_id}/offboard", response_model=OffboardResult, status_code=status.HTTP_201_CREATED)
async def offboard_person(person_id: uuid.UUID, session: SessionDep) -> OffboardResult:
    """Marks the person as left and creates a batch of delete actions, one per account, waiting for approval.

    Nothing is removed yet: approve the batch (approve_action_batch with ``batch_id``) to run the writes.
    Service accounts and accounts with an open action are skipped and listed.
    """
    return await offboarding.offboard_person(session, person_id)


@router.post("/{person_id}/onboard", response_model=OnboardResult, status_code=status.HTTP_201_CREATED)
async def onboard_person(person_id: uuid.UUID, data: OnboardRequest, session: SessionDep) -> OnboardResult:
    """Creates a batch of account creations in the chosen apps, waiting for approval.

    Apps whose connector cannot create accounts get a manual task. 400 when the person has left.
    """
    return await onboarding.onboard_person(session, person_id, data)
