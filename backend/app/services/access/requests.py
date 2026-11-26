"""Access requests: a person asks for an account in an app, in Slack (the agent), on the panel or through the API.

``request_access`` checks the request and stores it; ``flow.route`` sends it to its first step (the
manager, an admin, or nobody), by the app's ``request_policy``. Reading is in ``queries.py``.
"""

import dataclasses
from typing import TYPE_CHECKING

from sqlalchemy import select

from app.models import AccessRequest, App, Person
from app.models.enums import OPEN_REQUEST_STATUSES, AccessRequestChannel, PersonStatus, RequestPolicy
from app.services.access import flow
from app.services.access.decisions import record_event
from app.services.access.outcomes import Outcome, RequestResult, SlackOrigin
from app.services.errors import ConflictError, InvalidInputError
from app.services.onboarding import apps_with_account, apps_with_open_creation

if TYPE_CHECKING:
    import uuid

    from sqlalchemy.ext.asyncio import AsyncSession

    from app.services.action_dispatch import ActionDispatcher

JUSTIFICATION_NEEDED = "Say why you need it: the approver reads it next to the request."


@dataclasses.dataclass(frozen=True)
class NewRequest:
    """What the person asks for and who asks (``requested_by``: panel user e-mail, "e-mail (Slack)", token)."""

    justification: str | None
    requested_by: str
    role: str | None = None
    on_behalf: bool = False  # the person's manager asks for them
    origin: SlackOrigin | None = None  # asked in Slack: the agent answers there
    message: str | None = None


async def request_access(
    session: AsyncSession, *, person: Person, app: App, new: NewRequest, dispatcher: ActionDispatcher
) -> RequestResult:
    """Store the request and route it. 400: a leaver or no justification; 409: a request is already open."""
    if person.status == PersonStatus.LEFT:
        raise InvalidInputError("The person has left the company")
    name = app.name
    if app.request_policy == RequestPolicy.OFF:
        return RequestResult(Outcome.NOT_AVAILABLE, name)
    justification = (new.justification or "").strip()
    if not justification:
        raise InvalidInputError(JUSTIFICATION_NEEDED)
    if app.id in await apps_with_account(session, person.id, [app.id]):
        return RequestResult(Outcome.ALREADY_HAS_ACCOUNT, name)
    if await open_request(session, person.id, app.id) is not None:
        raise ConflictError(f"A request for {name} is already open. Wait for its decision.")
    if app.id in await apps_with_open_creation(session, person.id, [app.id]):
        return RequestResult(Outcome.ALREADY_REQUESTED, name)

    origin = new.origin
    request = AccessRequest(
        person_id=person.id,
        app_id=app.id,
        channel=AccessRequestChannel.SLACK if origin else AccessRequestChannel.PANEL,
        slack_user_id=origin.user_id if origin else None,
        slack_channel_id=origin.channel_id if origin else None,
        message=((origin.message if origin else new.message) or "")[:2000] or None,
        justification=justification[:2000],
        role=(new.role or "").strip()[:100] or None,
        requested_by=new.requested_by[:320],
        on_behalf=new.on_behalf,
    )
    session.add(request)
    await session.flush()
    request_id = request.id
    await record_event(
        session,
        request,
        "access_request.created",
        {"policy": str(app.request_policy), "channel": str(request.channel), "on_behalf": new.on_behalf},
    )
    result = await flow.route(session, request, person, app, dispatcher)
    return dataclasses.replace(result, request_id=request_id)


async def open_request(session: AsyncSession, person_id: uuid.UUID, app_id: uuid.UUID) -> AccessRequest | None:
    """The person's unfinished request for the app, if any."""
    return await session.scalar(
        select(AccessRequest)
        .where(
            AccessRequest.person_id == person_id,
            AccessRequest.app_id == app_id,
            AccessRequest.status.in_(OPEN_REQUEST_STATUSES),
        )
        .limit(1)
    )
