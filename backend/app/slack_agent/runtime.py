"""What every handler of a live Slack connection needs."""

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.services.action_dispatch import ActionDispatcher


@dataclass(frozen=True)
class SlackRuntime:
    bot_token: str
    bot_user_id: str | None
    bot_name: str
    dispatcher: ActionDispatcher
