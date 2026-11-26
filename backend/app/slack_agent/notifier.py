"""Tells people on Slack how their request ended, once its action is done, failed or cancelled."""

from datetime import UTC, datetime
from typing import TYPE_CHECKING

import structlog
from sqlalchemy import or_, select

from app.database import async_session
from app.models import AccessRequest, Action, App
from app.models.enums import OPEN_REQUEST_STATUSES, AccessRequestChannel
from app.services import audit
from app.services.access.requests import close, closing_status
from app.services.actions import FINISHED_STATUSES
from app.slack_agent import texts, web_api
from app.slack_agent.web_api import SlackApiError

if TYPE_CHECKING:
    from app.slack_agent.runtime import SlackRuntime

logger = structlog.get_logger()
BATCH = 20
# The person can no longer get the message: close the request anyway.
UNREACHABLE = frozenset({"channel_not_found", "is_archived", "user_not_found", "user_disabled"})


async def notify_finished(rt: SlackRuntime) -> None:
    async with async_session() as session:
        rows = (
            await session.execute(
                select(AccessRequest, Action, App.name)
                .join(App, App.id == AccessRequest.app_id)
                .outerjoin(Action, Action.id == AccessRequest.action_id)
                .where(
                    AccessRequest.status.in_(OPEN_REQUEST_STATUSES),
                    or_(Action.id.is_(None), Action.status.in_(FINISHED_STATUSES)),
                )
                .order_by(AccessRequest.created_at)
                .limit(BATCH)
                .with_for_update(of=AccessRequest, skip_locked=True)
            )
        ).all()
        for request, action, app_name in rows:
            status = closing_status(action.status if action else None)
            # A request from the panel only closes here: the "My access" page shows its result.
            if request.channel == AccessRequestChannel.SLACK:
                try:
                    await web_api.call(
                        "chat.postMessage",
                        rt.bot_token,
                        json={"channel": request.slack_channel_id, "text": texts.finished(app_name, status, action)},
                    )
                except SlackApiError as exc:
                    logger.warning("slack_agent_notify_failed", request_id=str(request.id), error=str(exc))
                    if exc.error not in UNREACHABLE:
                        continue  # stays open: the next poll tries again
                else:
                    request.notified_at = datetime.now(UTC)
            close(request, status)
            await audit.record(
                session,
                "access_request.closed",
                "access_request",
                request.id,
                {"status": str(request.status)},
                app_id=request.app_id,
                person_id=request.person_id,
            )
        await session.commit()
