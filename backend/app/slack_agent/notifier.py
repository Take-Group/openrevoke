"""Tells people on Slack how their request ended: done, failed, rejected (with the comment) or cancelled.

Every channel: a Slack request answers in its chat, a request from the panel or the API in a direct
message, when Slack knows one of the person's e-mails. Requests close when their action does
(``services/access/request_sync.py``), not here. Only requests closed in the last day are told,
so turning the bot on does not send old news; ``notified_at`` marks the ones told.
"""

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

import structlog
from sqlalchemy import select

from app.database import async_session
from app.models import AccessRequest, Action, App, Person
from app.services.access import managers
from app.services.access.decisions import CLOSED_STATUSES, last_rejection
from app.slack_agent import identity, texts, web_api
from app.slack_agent.web_api import SlackApiError

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from app.slack_agent.runtime import SlackRuntime

logger = structlog.get_logger()
BATCH = 200
TELL_WITHIN = timedelta(days=1)
# The person can no longer get the message: stop trying.
UNREACHABLE = frozenset({"channel_not_found", "is_archived", "user_not_found", "user_disabled"})


async def notify_finished(rt: SlackRuntime) -> None:
    async with async_session() as session:
        rows = (
            await session.execute(
                select(AccessRequest, Person, App.name, Action)
                .join(Person, Person.id == AccessRequest.person_id)
                .join(App, App.id == AccessRequest.app_id)
                .outerjoin(Action, Action.id == AccessRequest.action_id)
                .where(
                    AccessRequest.status.in_(CLOSED_STATUSES),
                    AccessRequest.notified_at.is_(None),
                    AccessRequest.closed_at >= datetime.now(UTC) - TELL_WITHIN,
                )
                .order_by(AccessRequest.closed_at)
                .limit(BATCH)
                .with_for_update(of=AccessRequest, skip_locked=True)
            )
        ).all()
        if not rows:
            return
        comments = await last_rejection(session, [request.id for request, *_ in rows])
        for request, person, app_name, action in rows:
            channel = request.slack_channel_id or await _direct_channel(session, rt, person)
            if channel is None:
                continue  # not on Slack: the panel shows the result
            text = texts.finished(app_name, request.status, action, comments.get(request.id))
            try:
                await web_api.call("chat.postMessage", rt.bot_token, json={"channel": channel, "text": text})
            except SlackApiError as exc:
                logger.warning("slack_agent_notify_failed", request_id=str(request.id), error=str(exc))
                if exc.error not in UNREACHABLE:
                    continue  # the next poll tries again
            request.notified_at = datetime.now(UTC)
        await session.commit()


async def _direct_channel(session: AsyncSession, rt: SlackRuntime, person: Person) -> str | None:
    """The person's Slack user id: posting to it opens the direct message with the bot."""
    for email in await managers.emails_of(session, person):
        try:
            slack_id = await identity.slack_user_for_email(rt.bot_token, email)
        except SlackApiError as exc:
            logger.warning("slack_agent_lookup_failed", error=str(exc))
            return None
        if slack_id:
            return slack_id
    return None
