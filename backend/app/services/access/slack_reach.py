"""Can a person decide on Slack: the bot is connected and Slack knows one of their e-mails.

Asked when a request picks its approver (a manager without a panel account may still decide
with the Slack buttons) and when the result goes back to the person who asked.
"""

from typing import TYPE_CHECKING

import structlog

from app.models import SlackAgent
from app.models.enums import SlackAgentStatus
from app.services import slack_agent_secrets as tokens
from app.slack_agent import identity
from app.slack_agent.web_api import SlackApiError

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = structlog.get_logger()


async def bot_token(session: AsyncSession) -> str | None:
    """The bot token while the agent is on and connected; None otherwise."""
    row = await session.get(SlackAgent, 1)
    if row is None or not row.enabled or row.status != SlackAgentStatus.CONNECTED:
        return None
    return tokens.read(row).get(tokens.BOT_TOKEN) or None


async def slack_user_id(session: AsyncSession, emails: list[str]) -> str | None:
    """The Slack user id of the first e-mail Slack knows; None without the bot or on a Slack error."""
    token = await bot_token(session)
    if token is None:
        return None
    for email in emails:
        try:
            user_id = await identity.slack_user_for_email(token, email)
        except (SlackApiError, OSError) as exc:
            logger.warning("slack_lookup_failed", error=str(exc))
            return None
        if user_id:
            return user_id
    return None
