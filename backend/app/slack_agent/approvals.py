"""Requests waiting for a decision go to the approver on Slack with Approve and Reject buttons.

By step, whatever the channel the person asked on: a request waiting for the manager goes to the
manager (found by their e-mails with ``users.lookupByEmail``), one waiting for an admin goes to every
admin with a Slack account except the person who asked. A click is checked by ``flow.decide``: the
manager (by the e-mail of their Slack profile) or an admin; a rejection from Slack has no comment
and is recorded "Rejected in Slack". The decision is ``via=slack``, by "e-mail (Slack)".
"""

import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

import structlog
from sqlalchemy import select

from app.config import settings
from app.database import async_session
from app.models import AccessRequest, App, Person, User
from app.models.enums import AccessRequestStatus, DecisionOutcome, DecisionVia, UserRole, UserStatus
from app.services.access import flow, managers
from app.services.auth.actor import ActorRef, set_actor
from app.services.errors import DomainError
from app.services.matching import match_email
from app.slack_agent import identity, texts, web_api
from app.slack_agent.web_api import SlackApiError

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from app.slack_agent.runtime import SlackRuntime

logger = structlog.get_logger()

APPROVE = "open_revoke_approve"
REJECT = "open_revoke_reject"
BATCH = 20
WAITING = (AccessRequestStatus.PENDING_MANAGER, AccessRequestStatus.PENDING_ADMIN)


async def notify_pending(rt: SlackRuntime) -> None:
    async with async_session() as session:
        rows = (
            await session.execute(
                select(AccessRequest, Person, App)
                .join(Person, Person.id == AccessRequest.person_id)
                .join(App, App.id == AccessRequest.app_id)
                .where(AccessRequest.status.in_(WAITING), AccessRequest.approvers_notified_at.is_(None))
                .order_by(AccessRequest.created_at)
                .limit(BATCH)
                .with_for_update(of=AccessRequest, skip_locked=True)
            )
        ).all()
        if not rows:
            return
        admins: list[tuple[str, str]] | None = None  # (e-mail, Slack id), read once per poll
        for request, person, app in rows:
            for_manager = request.status == AccessRequestStatus.PENDING_MANAGER
            try:
                if for_manager:
                    recipients = await _manager_ids(session, rt, request)
                else:
                    admins = admins if admins is not None else await _admin_ids(session, rt)
                    own = set(await managers.emails_of(session, person))
                    recipients = [slack_id for email, slack_id in admins if email not in own]
            except SlackApiError as exc:
                logger.warning("slack_agent_approver_lookup_failed", error=str(exc))
                continue  # the next poll tries again
            text = texts.approval_request(
                person_name=f"{person.first_name} {person.last_name}",
                person_email=person.primary_email,
                app_name=app.name,
                justification=request.justification or request.message,
                role=request.role,
                for_manager=for_manager,
                requested_by=request.requested_by if request.on_behalf else None,
            )
            path = f"/me/approvals/{request.id}" if for_manager else f"/requests/{request.id}"
            for slack_id in recipients:
                try:
                    await web_api.call(
                        "chat.postMessage",
                        rt.bot_token,
                        json={"channel": slack_id, "text": text, "blocks": _blocks(text, request.id, path)},
                    )
                except SlackApiError as exc:
                    logger.warning("slack_agent_approval_post_failed", error=str(exc))
            request.approvers_notified_at = datetime.now(UTC)  # also without anyone on Slack: no retry loop
        await session.commit()


async def _manager_ids(session: AsyncSession, rt: SlackRuntime, request: AccessRequest) -> list[str]:
    manager = await session.get(Person, request.approver_person_id) if request.approver_person_id else None
    if manager is None:
        return []
    for email in await managers.emails_of(session, manager):
        if slack_id := await identity.slack_user_for_email(rt.bot_token, email):
            return [slack_id]
    return []


async def _admin_ids(session: AsyncSession, rt: SlackRuntime) -> list[tuple[str, str]]:
    emails = await session.scalars(
        select(User.email).where(User.role == UserRole.ADMIN, User.status == UserStatus.ACTIVE)
    )
    return [
        (email, slack_id) for email in emails if (slack_id := await identity.slack_user_for_email(rt.bot_token, email))
    ]


async def handle_click(rt: SlackRuntime, payload: dict[str, Any]) -> None:
    clicked = (payload.get("actions") or [{}])[0]
    kind = clicked.get("action_id")
    if kind not in (APPROVE, REJECT):
        return
    channel = (payload.get("channel") or {}).get("id")
    message = payload.get("message") or {}
    user_id = (payload.get("user") or {}).get("id")
    try:
        request_id = uuid.UUID(str(clicked.get("value")))
    except ValueError:
        return
    email = await identity.slack_email(rt, user_id) if user_id else None
    if email is None:
        await web_api.call("chat.postMessage", rt.bot_token, json={"channel": channel, "text": texts.UNKNOWN_DECIDER})
        return
    async with async_session() as session:
        decider = await _decider(session, email)
        set_actor(decider.actor.label, decider.actor.user_id, DecisionVia.SLACK)
        outcome = DecisionOutcome.APPROVED if kind == APPROVE else DecisionOutcome.REJECTED
        try:
            await flow.decide(
                session, request_id, decider=decider, outcome=outcome, comment=None, dispatcher=rt.dispatcher
            )
            await session.commit()
            result = (
                f":white_check_mark: Approved by {email}."
                if outcome == DecisionOutcome.APPROVED
                else f":no_entry_sign: Rejected by {email}."
            )
        except DomainError as exc:
            await session.rollback()
            result = f":warning: Not done: {exc.message}"
    original = _original_text(message)
    await web_api.call(
        "chat.update",
        rt.bot_token,
        json={
            "channel": channel,
            "ts": message.get("ts"),
            "text": f"{original}\n{result}",
            "blocks": [_section(original), {"type": "context", "elements": [{"type": "mrkdwn", "text": result}]}],
        },
    )


async def _decider(session: AsyncSession, email: str) -> flow.Decider:
    """The Slack user as a decider: their panel account (if any) and the person with their e-mail."""
    user = await session.scalar(select(User).where(User.email == email, User.status == UserStatus.ACTIVE))
    person_id = (await match_email(session, email)).person_id
    actor = ActorRef(f"{email} (Slack)", user.id if user else None, DecisionVia.SLACK)
    return flow.Decider(actor=actor, person_id=person_id, is_admin=user is not None and user.role == UserRole.ADMIN)


def _blocks(text: str, request_id: uuid.UUID, path: str) -> list[dict[str, Any]]:
    value = str(request_id)
    return [
        _section(text),
        {
            "type": "actions",
            "elements": [
                _button("Approve", APPROVE, value, "primary"),
                _button("Reject", REJECT, value, "danger"),
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "Open in Open Revoke"},
                    "url": f"{settings.public_url}{path}",
                    "action_id": "open_revoke_link",
                },
            ],
        },
    ]


def _button(label: str, action_id: str, value: str, style: str) -> dict[str, Any]:
    return {
        "type": "button",
        "text": {"type": "plain_text", "text": label},
        "action_id": action_id,
        "value": value,
        "style": style,
    }


def _section(text: str) -> dict[str, Any]:
    return {"type": "section", "text": {"type": "mrkdwn", "text": text}}


def _original_text(message: dict[str, Any]) -> str:
    for block in message.get("blocks") or []:
        if block.get("type") == "section":
            return str((block.get("text") or {}).get("text") or "")
    return str(message.get("text") or "")
