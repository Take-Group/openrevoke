"""Offboarding: one click creates a batch of actions for all accounts of a person.

The person becomes ``left``. Every not-removed account gets a
``delete_account`` action, or a ``manual_task`` when the app's connector
cannot delete. All actions wait for approval and
share one ``batch_id``. Service accounts and accounts with an open action
are skipped and reported.
"""

import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import select

from app.models import Account, Action, App, Person
from app.models.enums import AccountKind, AccountStatus, ActionKind, ActionReason, PersonStatus
from app.schemas.actions import ActionCreate, OffboardResult, OffboardSkipped, OffboardSkipReason, WriteKind
from app.services import audit
from app.services.action_queries import get_actions_out
from app.services.actions import OPEN_STATUSES, create_action
from app.services.errors import NotFoundError
from app.services.presenters import account_ref, app_ref, person_ref

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

REMOVING_KINDS = (ActionKind.DELETE_ACCOUNT, ActionKind.MANUAL_TASK)


async def offboard_person(session: AsyncSession, person_id: uuid.UUID) -> OffboardResult:
    person = await session.get(Person, person_id)
    if person is None:
        raise NotFoundError("Person not found")
    batch_id = uuid.uuid4()
    if person.status != PersonStatus.LEFT:
        person.status = PersonStatus.LEFT
        person.left_at = datetime.now(UTC)

    rows = await session.execute(
        select(Account, App)
        .join(App, App.id == Account.app_id)
        .where(Account.person_id == person.id, Account.status != AccountStatus.REMOVED)
        .order_by(App.name, Account.id)
    )
    accounts = list(rows)
    busy = set(
        await session.scalars(
            select(Action.account_id).where(
                Action.account_id.in_([account.id for account, _ in accounts]),
                Action.status.in_(OPEN_STATUSES),
                Action.kind.in_(REMOVING_KINDS),
            )
        )
    )

    action_ids: list[uuid.UUID] = []
    skipped: list[OffboardSkipped] = []
    for account, app in accounts:
        reason = None
        if account.kind == AccountKind.SERVICE:
            reason = OffboardSkipReason.SERVICE_ACCOUNT
        elif account.id in busy:
            reason = OffboardSkipReason.ACTION_OPEN
        if reason is not None:
            skipped.append(OffboardSkipped(account=account_ref(account), app=app_ref(app), reason=reason))
            continue
        action = await create_action(
            session,
            ActionCreate(kind=WriteKind.DELETE_ACCOUNT, app_id=app.id, person_id=person.id, account_id=account.id),
            reason=ActionReason.OFFBOARDING,
            batch_id=batch_id,
        )
        action_ids.append(action.id)

    await session.flush()
    await audit.record(
        session,
        "person.offboarded",
        "person",
        person.id,
        {"batch_id": str(batch_id), "actions": len(action_ids), "skipped": len(skipped)},
    )
    from app.services.access.flow import reroute_pending  # late: flow imports the action services

    await reroute_pending(session)  # requests that waited for this person as manager go elsewhere
    return OffboardResult(
        batch_id=batch_id,
        person=person_ref(person),
        actions=await get_actions_out(session, action_ids),
        skipped=skipped,
    )
