"""Onboarding: one click creates a batch of actions that give a person accounts in chosen apps.

Every chosen app gets a ``create_account`` action, or a ``manual_task`` when
the app's connector cannot create accounts. All actions wait for approval and
share one ``batch_id``. Apps where the person already has an account, or an
open creation, are skipped and reported. A person who has left cannot be
onboarded: set them active first.

A ``role`` per app (typed in the panel or given by an access profile) goes into the action's
payload and from there into the connector's create request.
"""

import uuid
from dataclasses import dataclass
from typing import TYPE_CHECKING

from sqlalchemy import and_, or_, select

from app.models import Account, Action, App, Connection, Person
from app.models.enums import AccountStatus, ActionKind, ActionReason, PersonStatus
from app.schemas.actions import (
    ActionCreate,
    OnboardApp,
    OnboardRequest,
    OnboardResult,
    OnboardSkipped,
    OnboardSkipReason,
    WriteKind,
    WriteMode,
)
from app.services import audit
from app.services.action_queries import get_actions_out
from app.services.actions import OPEN_STATUSES, create_action
from app.services.capabilities import write_mode
from app.services.errors import InvalidInputError, NotFoundError
from app.services.matching import is_valid_email, normalize_email
from app.services.presenters import app_ref, person_ref

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


@dataclass(frozen=True)
class PlannedApp:
    """One requested app: skipped (``skip``) or what its creation will do (``write_mode``)."""

    app: App
    role: str | None
    skip: OnboardSkipReason | None
    write_mode: WriteMode


async def onboardable_person(session: AsyncSession, person_id: uuid.UUID) -> Person:
    person = await session.get(Person, person_id)
    if person is None:
        raise NotFoundError("Person not found")
    if person.status == PersonStatus.LEFT:
        raise InvalidInputError("The person has left. Set them active before onboarding")
    return person


async def plan(session: AsyncSession, person: Person, apps: list[OnboardApp]) -> list[PlannedApp]:
    """What onboarding would do per app, in request order, without saving anything.

    Used by ``onboard_person`` and by the access profile preview (``services.access.profile_assignment``).
    """
    requested = _unique(apps)
    found = {app.id: app for app in await session.scalars(select(App).where(App.id.in_(requested)))}
    missing = [str(app_id) for app_id in requested if app_id not in found]
    if missing:
        raise InvalidInputError(f"App not found: {', '.join(missing)}")
    connections = {
        connection.app_id: connection
        for connection in await session.scalars(select(Connection).where(Connection.app_id.in_(requested)))
    }
    has_account = await apps_with_account(session, person.id, list(requested))
    creating = await apps_with_open_creation(session, person.id, list(requested))
    planned = []
    for app_id, item in requested.items():
        skip = None
        if app_id in has_account:
            skip = OnboardSkipReason.HAS_ACCOUNT
        elif app_id in creating:
            skip = OnboardSkipReason.ACTION_OPEN
        role = (item.role or "").strip() or None
        mode = write_mode(connections.get(app_id), WriteKind.CREATE_ACCOUNT)
        planned.append(PlannedApp(app=found[app_id], role=role, skip=skip, write_mode=mode))
    return planned


async def onboard_person(
    session: AsyncSession,
    person_id: uuid.UUID,
    data: OnboardRequest,
    *,
    audit_note: dict[str, object] | None = None,
) -> OnboardResult:
    """Creates the actions. Each carries the app's ``role`` from the request into its payload (and the
    connector's create request). ``audit_note`` adds context to the ``person.onboarded`` event."""
    person = await onboardable_person(session, person_id)
    email = normalize_email(data.email)
    if email is not None and not is_valid_email(email):
        raise InvalidInputError(f"Invalid email: {data.email!r}")

    batch_id = uuid.uuid4()
    action_ids: list[uuid.UUID] = []
    skipped: list[OnboardSkipped] = []
    for item in await plan(session, person, data.apps):
        if item.skip is not None:
            skipped.append(OnboardSkipped(app=app_ref(item.app), reason=item.skip))
            continue
        action = await create_action(
            session,
            ActionCreate(
                kind=WriteKind.CREATE_ACCOUNT, app_id=item.app.id, person_id=person.id, email=email, role=item.role
            ),
            reason=ActionReason.ONBOARDING,
            batch_id=batch_id,
        )
        action_ids.append(action.id)

    await session.flush()
    await audit.record(
        session,
        "person.onboarded",
        "person",
        person.id,
        {"batch_id": str(batch_id), "actions": len(action_ids), "skipped": len(skipped), **(audit_note or {})},
    )
    return OnboardResult(
        batch_id=batch_id,
        person=person_ref(person),
        actions=await get_actions_out(session, action_ids),
        skipped=skipped,
    )


def _unique(apps: list[OnboardApp]) -> dict[uuid.UUID, OnboardApp]:
    """Request order, the first entry of a repeated app wins."""
    unique: dict[uuid.UUID, OnboardApp] = {}
    for item in apps:
        unique.setdefault(item.app_id, item)
    return unique


async def apps_with_account(session: AsyncSession, person_id: uuid.UUID, app_ids: list[uuid.UUID]) -> set[uuid.UUID]:
    return set(
        await session.scalars(
            select(Account.app_id).where(
                Account.person_id == person_id,
                Account.app_id.in_(app_ids),
                Account.status != AccountStatus.REMOVED,
            )
        )
    )


async def apps_with_open_creation(
    session: AsyncSession, person_id: uuid.UUID, app_ids: list[uuid.UUID]
) -> set[uuid.UUID]:
    """Apps with an open create_account action, or an open manual task to create the account."""
    return set(
        await session.scalars(
            select(Action.app_id).where(
                Action.person_id == person_id,
                Action.app_id.in_(app_ids),
                Action.status.in_(OPEN_STATUSES),
                or_(
                    Action.kind == ActionKind.CREATE_ACCOUNT,
                    and_(
                        Action.kind == ActionKind.MANUAL_TASK,
                        Action.payload["operation"].astext == WriteKind.CREATE_ACCOUNT,
                    ),
                ),
            )
        )
    )
