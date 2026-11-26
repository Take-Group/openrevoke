"""Reading access requests for the API: lists with filters, one request with its decisions, CSV export."""

import csv
import io
from dataclasses import dataclass
from typing import TYPE_CHECKING

from sqlalchemy import func, select

from app.models import AccessRequest, AccessRequestDecision, Action, App
from app.models.enums import AccessRequestStatus, ActionStatus
from app.schemas.access_requests import (
    AccessRequestActionOut,
    AccessRequestDecisionOut,
    AccessRequestDetail,
    AccessRequestOut,
    AccessRequestPage,
    WaitingFor,
)
from app.services.access.decisions import last_rejection, people_by_id
from app.services.costs import monthly_price
from app.services.errors import NotFoundError
from app.services.presenters import app_ref, money, person_ref, price_of

if TYPE_CHECKING:
    import uuid
    from datetime import datetime

    from sqlalchemy import Select
    from sqlalchemy.ext.asyncio import AsyncSession

    from app.models import Person

WAITING_STATUS: dict[str, AccessRequestStatus] = {
    "manager": AccessRequestStatus.PENDING_MANAGER,
    "admin": AccessRequestStatus.PENDING_ADMIN,
}
EXPORT_LIMIT = 50_000


@dataclass(frozen=True)
class RequestFilter:
    statuses: list[AccessRequestStatus] | None = None
    app_id: uuid.UUID | None = None
    person_id: uuid.UUID | None = None
    approver_person_id: uuid.UUID | None = None
    created_from: datetime | None = None
    created_to: datetime | None = None
    waiting_for: WaitingFor | None = None


def waiting_for(status: AccessRequestStatus) -> WaitingFor | None:
    if status == AccessRequestStatus.PENDING_MANAGER:
        return "manager"
    if status == AccessRequestStatus.PENDING_ADMIN:
        return "admin"
    return None


def _filtered(f: RequestFilter) -> Select[tuple[AccessRequest]]:
    query = select(AccessRequest)
    if f.statuses:
        query = query.where(AccessRequest.status.in_(f.statuses))
    if f.waiting_for is not None:
        query = query.where(AccessRequest.status == WAITING_STATUS[f.waiting_for])
    if f.app_id is not None:
        query = query.where(AccessRequest.app_id == f.app_id)
    if f.person_id is not None:
        query = query.where(AccessRequest.person_id == f.person_id)
    if f.approver_person_id is not None:
        query = query.where(AccessRequest.approver_person_id == f.approver_person_id)
    if f.created_from is not None:
        query = query.where(AccessRequest.created_at >= f.created_from)
    if f.created_to is not None:
        query = query.where(AccessRequest.created_at < f.created_to)
    return query


async def list_requests(session: AsyncSession, f: RequestFilter, *, limit: int, offset: int) -> AccessRequestPage:
    query = _filtered(f)
    total = await session.scalar(select(func.count()).select_from(query.subquery())) or 0
    rows = list(
        await session.scalars(
            query.order_by(AccessRequest.created_at.desc(), AccessRequest.id.desc()).limit(limit).offset(offset)
        )
    )
    return AccessRequestPage(items=await present(session, rows), total=total)


async def count(session: AsyncSession, f: RequestFilter) -> int:
    return await session.scalar(select(func.count()).select_from(_filtered(f).subquery())) or 0


async def present(session: AsyncSession, rows: list[AccessRequest]) -> list[AccessRequestOut]:
    people = await people_by_id(session, {r.person_id for r in rows} | {r.approver_person_id for r in rows})
    apps = {a.id: a for a in await session.scalars(select(App).where(App.id.in_({r.app_id for r in rows})))}
    action_ids = {r.action_id for r in rows if r.action_id}
    statuses = dict((await session.execute(select(Action.id, Action.status).where(Action.id.in_(action_ids)))).all())
    rejected = await last_rejection(
        session, [r.id for r in rows if r.status == AccessRequestStatus.REJECTED or r.closed_at is not None]
    )
    return [
        _out(row, people, apps[row.app_id], statuses.get(row.action_id) if row.action_id else None, rejected)
        for row in rows
    ]


def _out(
    row: AccessRequest,
    people: dict[uuid.UUID, Person],
    app: App,
    action_status: ActionStatus | None,
    rejected: dict[uuid.UUID, str | None],
) -> AccessRequestOut:
    return AccessRequestOut(
        id=row.id,
        person=person_ref(people[row.person_id]),
        app=app_ref(app),
        action_id=row.action_id,
        action_status=action_status,
        channel=row.channel,
        status=row.status,
        waiting_for=waiting_for(row.status),
        approver=person_ref(people.get(row.approver_person_id)) if row.approver_person_id else None,
        fallback_reason=row.fallback_reason,
        justification=row.justification,
        role=row.role,
        message=row.message,
        requested_by=row.requested_by,
        on_behalf=row.on_behalf,
        rejection_comment=rejected.get(row.id) if row.status == AccessRequestStatus.REJECTED else None,
        created_at=row.created_at,
        closed_at=row.closed_at,
        notified_at=row.notified_at,
    )


async def get_request(session: AsyncSession, request_id: uuid.UUID) -> AccessRequest:
    request = await session.get(AccessRequest, request_id, populate_existing=True)
    if request is None:
        raise NotFoundError("Access request not found")
    return request


async def detail(session: AsyncSession, request_id: uuid.UUID) -> AccessRequestDetail:
    request = await get_request(session, request_id)
    app = await session.get(App, request.app_id)
    assert app is not None
    (base,) = await present(session, [request])
    action = await session.get(Action, request.action_id) if request.action_id else None
    return AccessRequestDetail(
        **base.model_dump(),
        policy=app.request_policy,
        seat_monthly_cost=money(monthly_price(price_of(app))),
        decisions=[AccessRequestDecisionOut.model_validate(d) for d in await decisions_of(session, request.id)],
        action=AccessRequestActionOut(
            id=action.id,
            kind=action.kind,
            status=action.status,
            approved_by=action.approved_by,
            approved_at=action.approved_at,
            finished_at=action.finished_at,
            error=action.error,
        )
        if action
        else None,
    )


async def decisions_of(session: AsyncSession, request_id: uuid.UUID) -> list[AccessRequestDecision]:
    return list(
        await session.scalars(
            select(AccessRequestDecision)
            .where(AccessRequestDecision.request_id == request_id)
            .order_by(AccessRequestDecision.decided_at, AccessRequestDecision.id)
        )
    )


EXPORT_COLUMNS = [
    "request_id",
    "created_at",
    "status",
    "person",
    "person_email",
    "app",
    "role",
    "justification",
    "requested_by",
    "on_behalf",
    "channel",
    "manager",
    "fallback_reason",
    "decisions",
    "action_status",
    "action_approved_by",
    "closed_at",
]


async def export_csv(session: AsyncSession, f: RequestFilter) -> str:
    """Every request matching the filter with its decisions (one cell, ``;``-separated), oldest first."""
    rows = list(
        await session.scalars(_filtered(f).order_by(AccessRequest.created_at, AccessRequest.id).limit(EXPORT_LIMIT))
    )
    people = await people_by_id(session, {r.person_id for r in rows} | {r.approver_person_id for r in rows})
    apps = {a.id: a.name for a in await session.scalars(select(App).where(App.id.in_({r.app_id for r in rows})))}
    action_ids = {r.action_id for r in rows if r.action_id}
    actions = {a.id: a for a in await session.scalars(select(Action).where(Action.id.in_(action_ids)))}
    decisions: dict[uuid.UUID, list[str]] = {}
    for d in await session.scalars(
        select(AccessRequestDecision)
        .where(AccessRequestDecision.request_id.in_([r.id for r in rows]))
        .order_by(AccessRequestDecision.decided_at)
    ):
        text = f"{d.decided_at.isoformat()} {d.step} {d.decision} by {d.decided_by} via {d.via}"
        text += " (for the manager)" if d.override else ""
        text += f": {d.comment}" if d.comment else ""
        decisions.setdefault(d.request_id, []).append(text)
    out = io.StringIO()
    writer = csv.writer(out)
    writer.writerow(EXPORT_COLUMNS)
    for r in rows:
        person, manager = people[r.person_id], people.get(r.approver_person_id) if r.approver_person_id else None
        action = actions.get(r.action_id) if r.action_id else None
        cells = [
            r.id,
            r.created_at.isoformat(),
            r.status,
            f"{person.first_name} {person.last_name}",
            person.primary_email,
            apps.get(r.app_id, ""),
            r.role,
            r.justification,
            r.requested_by,
            "yes" if r.on_behalf else "no",
            r.channel,
            manager.primary_email if manager else "",
            r.fallback_reason,
            "; ".join(decisions.get(r.id, [])),
            action.status if action else "",
            action.approved_by if action else "",
            r.closed_at.isoformat() if r.closed_at else "",
        ]
        writer.writerow([_safe(None if cell is None else str(cell)) for cell in cells])
    return out.getvalue()


def _safe(value: str | None) -> str:
    """Every cell: names, roles and notes come from people, syncs and the Slack model. A leading
    = + - @ (or a tab or carriage return before one) would run as a formula in a spreadsheet."""
    text = value or ""
    return f"'{text}" if text[:1] in ("=", "+", "-", "@", "\t", "\r") else text
