"""What arrives over Socket Mode: direct messages to the bot and clicks on its buttons."""

from typing import TYPE_CHECKING, Any

from app.redis import redis_client
from app.slack_agent import approvals, conversation

if TYPE_CHECKING:
    from app.slack_agent.runtime import SlackRuntime

SEEN_KEY = "open-revoke:slack-agent:event:{event_id}"
SEEN_SECONDS = 3600


async def handle_envelope(rt: SlackRuntime, envelope: dict[str, Any]) -> None:
    payload = envelope.get("payload") or {}
    kind = envelope.get("type")
    if kind == "events_api":
        event = payload.get("event") or {}
        if not is_direct_message(event, rt.bot_user_id):
            return
        if not await _first_time(str(payload.get("event_id") or "")):
            return  # Slack retried an event we already handle
        await conversation.handle_message(
            rt, user_id=event["user"], channel_id=event["channel"], text=str(event.get("text") or "")
        )
    elif kind == "interactive" and payload.get("type") == "block_actions":
        await approvals.handle_click(rt, payload)


def is_direct_message(event: dict[str, Any], bot_user_id: str | None) -> bool:
    """A person's new message in a DM with the bot: not the bot's own, not an edit or a join."""
    return (
        event.get("type") == "message"
        and event.get("channel_type") == "im"
        and not event.get("subtype")
        and not event.get("bot_id")
        and bool(event.get("user"))
        and event.get("user") != bot_user_id
        and bool(str(event.get("text") or "").strip())
        and bool(event.get("channel"))
    )


async def _first_time(event_id: str) -> bool:
    if not event_id:
        return True
    return bool(await redis_client.set(SEEN_KEY.format(event_id=event_id), "1", nx=True, ex=SEEN_SECONDS))
