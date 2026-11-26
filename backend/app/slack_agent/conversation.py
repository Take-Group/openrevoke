"""One direct message to the agent: find the person, ask the model, replace the placeholder with the answer.

History: the last turns of each person are kept in Redis for a day, text only.
Messages of one person are answered one at a time (a lock per Slack user).
"""

import asyncio
import json
from collections import defaultdict
from typing import TYPE_CHECKING

import structlog

from app.ai.base import AiError, ChatTurn
from app.database import async_session
from app.models import Organization
from app.models.enums import PersonStatus
from app.redis import redis_client
from app.services.access.requests import SlackOrigin
from app.services.ai_settings import load_model
from app.services.auth.actor import current_actor
from app.slack_agent import identity, texts, web_api
from app.slack_agent.prompt import Requester, system_prompt
from app.slack_agent.tools import TOOLS, AgentTools

if TYPE_CHECKING:
    from app.slack_agent.runtime import SlackRuntime

logger = structlog.get_logger()

HISTORY_KEY = "open-revoke:slack-agent:history:{user_id}"
HISTORY_TURNS = 20
HISTORY_TTL_SECONDS = 24 * 3600
MAX_MESSAGE_CHARS = 4000

_locks: defaultdict[str, asyncio.Lock] = defaultdict(asyncio.Lock)


async def handle_message(rt: SlackRuntime, *, user_id: str, channel_id: str, text: str) -> None:
    async with _locks[user_id]:
        await _answer(rt, user_id=user_id, channel_id=channel_id, text=text[:MAX_MESSAGE_CHARS])


async def _answer(rt: SlackRuntime, *, user_id: str, channel_id: str, text: str) -> None:
    async with async_session() as session:
        person, email = await identity.find_person(session, rt, user_id)
        model = await load_model(session)
        organization = await session.get(Organization, 1)
    if person is None:
        await _post(rt, channel_id, texts.unknown_person(email))
        return
    if person.status == PersonStatus.LEFT:
        await _post(rt, channel_id, texts.LEFT)
        return
    if model is None:
        await _post(rt, channel_id, texts.NO_MODEL)
        return

    current_actor.set(f"{person.primary_email} (Slack)")  # audit events of this turn name the person
    placeholder = await _post(rt, channel_id, texts.WORKING)
    history = await _load_history(user_id)
    history.append(ChatTurn(role="user", text=text))
    tools = AgentTools(
        person_id=person.id,
        origin=SlackOrigin(user_id=user_id, channel_id=channel_id, message=text),
        dispatcher=rt.dispatcher,
    )
    prompt = system_prompt(
        bot_name=rt.bot_name,
        organization=organization.name if organization else "the company",
        requester=Requester(name=f"{person.first_name} {person.last_name}".strip(), email=person.primary_email),
    )
    try:
        answer = await model.reply(system=prompt, history=history, tools=TOOLS, execute=tools.execute)
    except AiError as exc:
        logger.warning("slack_agent_model_failed", error=str(exc))
        answer = texts.AI_FAILED.format(error=exc)
    except Exception:
        logger.exception("slack_agent_turn_failed")
        answer = texts.FAILED
    else:
        answer = answer or "…"
        await _save_history(user_id, [*history, ChatTurn(role="assistant", text=answer)])
    await _replace(rt, channel_id, placeholder, answer)


async def _post(rt: SlackRuntime, channel_id: str, text: str) -> str | None:
    body = await web_api.call("chat.postMessage", rt.bot_token, json={"channel": channel_id, "text": text})
    return body.get("ts")


async def _replace(rt: SlackRuntime, channel_id: str, ts: str | None, text: str) -> None:
    if ts is None:
        await _post(rt, channel_id, text)
        return
    await web_api.call("chat.update", rt.bot_token, json={"channel": channel_id, "ts": ts, "text": text})


async def _load_history(user_id: str) -> list[ChatTurn]:
    raw = await redis_client.get(HISTORY_KEY.format(user_id=user_id))
    try:
        items = json.loads(raw) if raw else []
    except ValueError:
        return []
    return [
        ChatTurn(role=item["role"], text=item["text"]) for item in items if item.get("role") in ("user", "assistant")
    ]


async def _save_history(user_id: str, turns: list[ChatTurn]) -> None:
    kept = turns[-HISTORY_TURNS:]
    while kept and kept[0].role != "user":  # a conversation sent to the model starts with the person
        kept = kept[1:]
    data = json.dumps([{"role": turn.role, "text": turn.text} for turn in kept], ensure_ascii=False)
    await redis_client.set(HISTORY_KEY.format(user_id=user_id), data, ex=HISTORY_TTL_SECONDS)
