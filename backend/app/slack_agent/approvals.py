"""Requests waiting for approval go to the admins on Slack with Approve and Reject buttons.

Admins are panel users with the admin role whose e-mail has a Slack account.
A click is accepted only from such an admin; the audit log names them.
"""

import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

import structlog
from sqlalchemy import select

from app.config import settings
from app.database import async_session
from app.models import AccessRequest, Action, App, Person, User
from app.models.enums import AccessRequestStatus, ActionStatus, UserRole
from app.services.action_approval import approve
from app.services.actions import cancel
from app.services.auth.actor import current_actor
from app.services.errors import DomainError
from app.slack_agent import identity, texts, web_api
from app.slack_agent.web_api import SlackApiError

if TYPE_CHECKING:
    from app.slack_agent.runtime import SlackRuntime

logger = structlog.get_logger()

APPROVE = "open_revoke_approve"
REJECT = "open_revoke_reject"
BATCH = 20


async def notify_pending(rt: SlackRuntime) -> None:
    async with async_session() as session:
        rows = (
            await session.execute(
                select(AccessRequest, Person, App)
                .join(Action, Action.id == AccessRequest.action_id)
                .join(Person, Person.id == AccessRequest.person_id)
                .join(App, App.id == AccessRequest.app_id)
                .where(
                    AccessRequest.status == AccessRequestStatus.OPEN,
                    AccessRequest.approvers_notified_at.is_(None),
                    Action.status == ActionStatus.PENDING_APPROVAL,
                )
                .order_by(AccessRequest.created_at)
                .limit(BATCH)
                .with_for_update(of=AccessRequest, skip_locked=True)
            )
        ).all()
        if not rows:
            return
        admin_emails = list(await session.scalars(select(User.email).where(User.role == UserRole.ADMIN)))
        admin_ids = [user_id for email in admin_emails if (user_id := await identity.slack_user_for_email(rt, email))]
        for request, person, app in rows:
            text = texts.approval_request(
                f"{person.first_name} {person.last_name}", person.primary_email, app.name, request.message
            )
            for admin_id in admin_ids:
                try:
                    await web_api.call(
                        "chat.postMessage",
                        rt.bot_token,
                        json={"channel": admin_id, "text": text, "blocks": _blocks(text, request.action_id)},
                    )
                except SlackApiError as exc:
                    logger.warning("slack_agent_approval_post_failed", error=str(exc))
            request.approvers_notified_at = datetime.now(UTC)  # also without admins on Slack: no retry loop
        await session.commit()


async def handle_click(rt: SlackRuntime, payload: dict[str, Any]) -> None:
    clicked = (payload.get("actions") or [{}])[0]
    kind = clicked.get("action_id")
    if kind not in (APPROVE, REJECT):
        return
    channel = (payload.get("channel") or {}).get("id")
    message = payload.get("message") or {}
    user_id = (payload.get("user") or {}).get("id")
    try:
        action_id = uuid.UUID(str(clicked.get("value")))
    except ValueError:
        return
    async with async_session() as session:
        admin = await identity.find_admin(session, rt, user_id) if user_id else None
        if admin is None:
            await web_api.call("chat.postMessage", rt.bot_token, json={"channel": channel, "text": texts.ADMIN_ONLY})
            return
        admin_name = admin.name  # approve() expires the session's objects
        current_actor.set(f"{admin.email} (Slack)")
        try:
            if kind == APPROVE:
                await approve(session, action_id, rt.dispatcher)
                outcome = f":white_check_mark: Approved by {admin_name}."
            else:
                await cancel(session, action_id)
                outcome = f":no_entry_sign: Rejected by {admin_name}."
            await session.commit()
        except DomainError as exc:
            await session.rollback()
            outcome = f":warning: Not done: {exc.message}"
    original = _original_text(message)
    await web_api.call(
        "chat.update",
        rt.bot_token,
        json={
            "channel": channel,
            "ts": message.get("ts"),
            "text": f"{original}\n{outcome}",
            "blocks": [_section(original), {"type": "context", "elements": [{"type": "mrkdwn", "text": outcome}]}],
        },
    )


def _blocks(text: str, action_id: uuid.UUID | None) -> list[dict[str, Any]]:
    value = str(action_id)
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
                    "url": f"{settings.public_url}/actions?tab=pending",
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
