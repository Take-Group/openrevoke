"""OpenAI, OpenRouter and any OpenAI-compatible endpoint through the ``openai`` SDK (Chat Completions).

The reasoning level goes out as ``reasoning_effort``, except on OpenRouter, which takes
``reasoning.effort``. ``GET /models`` says which models reason only on OpenRouter
(``supported_parameters``); elsewhere a model's levels are unknown and the test call checks them.
"""

import json
from typing import Any

import openai
from openai import AsyncOpenAI

from app.ai.base import (
    MAX_TOOL_ROUNDS,
    REQUEST_TIMEOUT_SECONDS,
    AiError,
    ChatTurn,
    ModelOption,
    ToolExecutor,
    ToolSpec,
    run_tool,
)
from app.models.enums import AiReasoningEffort

# Levels the Chat Completions ``reasoning_effort`` takes on every reasoning model.
CHAT_EFFORTS = (AiReasoningEffort.LOW, AiReasoningEffort.MEDIUM, AiReasoningEffort.HIGH)
# OpenAI lists every model of the account; these words mark ones that cannot chat.
NOT_CHAT = ("embedding", "tts", "whisper", "dall-e", "moderation", "transcribe", "image", "audio", "realtime", "search")


class OpenAiCompatibleModel:
    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        base_url: str | None = None,
        label: str = "OpenAI",
        headers: dict[str, str] | None = None,
        effort: AiReasoningEffort | None = None,
        openrouter: bool = False,
        chat_only: bool = False,
    ) -> None:
        self._model = model
        self._label = label
        self._effort = effort
        self._openrouter = openrouter
        self._chat_only = chat_only
        self._client = AsyncOpenAI(
            api_key=api_key or "none",  # local endpoints often take no key, the SDK needs a value
            base_url=base_url or None,
            timeout=REQUEST_TIMEOUT_SECONDS,
            max_retries=2,
            default_headers=headers,
        )

    async def reply(self, *, system: str, history: list[ChatTurn], tools: list[ToolSpec], execute: ToolExecutor) -> str:
        messages: list[dict[str, Any]] = [{"role": "system", "content": system}]
        messages += [{"role": turn.role, "content": turn.text} for turn in history]
        tool_defs = [
            {"type": "function", "function": {"name": t.name, "description": t.description, "parameters": t.parameters}}
            for t in tools
        ]
        for _ in range(MAX_TOOL_ROUNDS):
            params: dict[str, Any] = {"model": self._model, "messages": messages}
            if tool_defs:
                params["tools"] = tool_defs
            params.update(self._effort_params())
            try:
                response = await self._client.chat.completions.create(**params)
            except openai.APIError as exc:
                raise self._error(exc) from exc
            if not response.choices:
                raise AiError(f"{self._label} returned no answer")
            message = response.choices[0].message
            calls = message.tool_calls or []
            if not calls:
                return (message.content or "").strip()
            messages.append(
                {
                    "role": "assistant",
                    "content": message.content,
                    "tool_calls": [
                        {
                            "id": call.id,
                            "type": "function",
                            "function": {"name": call.function.name, "arguments": call.function.arguments},
                        }
                        for call in calls
                        if call.type == "function"
                    ],
                }
            )
            for call in calls:
                if call.type != "function":
                    continue
                output, is_error = await run_tool(execute, call.function.name, _arguments(call.function.arguments))
                content = f"Error: {output}" if is_error else output
                messages.append({"role": "tool", "tool_call_id": call.id, "content": content})
        raise AiError(f"The model called tools more than {MAX_TOOL_ROUNDS} times in one answer")

    async def list_models(self) -> list[ModelOption]:
        try:
            models = [model async for model in self._client.models.list()]
        except openai.APIError as exc:
            raise self._error(exc) from exc
        options = [
            ModelOption(id=model.id, name=_name(model), efforts=self._efforts(model))
            for model in models
            if not (self._chat_only and any(word in model.id for word in NOT_CHAT))
        ]
        return sorted(options, key=lambda option: option.id)

    def _effort_params(self) -> dict[str, Any]:
        if not self._effort:
            return {}
        if self._openrouter:
            return {"extra_body": {"reasoning": {"effort": str(self._effort)}}}
        return {"reasoning_effort": str(self._effort)}

    def _efforts(self, model: Any) -> tuple[AiReasoningEffort, ...] | None:
        if not self._openrouter:
            return None
        supported = (model.model_extra or {}).get("supported_parameters") or []
        return CHAT_EFFORTS if "reasoning" in supported or "reasoning_effort" in supported else ()

    def _error(self, exc: openai.APIError) -> AiError:
        name = self._label
        if isinstance(exc, openai.AuthenticationError):
            return AiError(f"{name} rejected the API key")
        if isinstance(exc, openai.PermissionDeniedError):
            return AiError(f"The {name} API key has no access to this model")
        if isinstance(exc, openai.NotFoundError):
            return AiError(f"{name} does not know this model or endpoint. Check the model and the base URL")
        if isinstance(exc, openai.RateLimitError):
            return AiError(f"{name} rate limit or quota reached")
        if isinstance(exc, openai.BadRequestError):
            return AiError(f"{name} refused the request: {exc.message}")
        if isinstance(exc, openai.APIStatusError):
            return AiError(f"{name} error {exc.status_code}: {exc.message}")
        if isinstance(exc, openai.APIConnectionError):
            return AiError(f"Cannot reach {name}. Check the base URL")
        return AiError(f"{name} error: {exc}")


def _name(model: Any) -> str:
    """OpenRouter sends a display ``name``; OpenAI and most endpoints only the id."""
    name = (model.model_extra or {}).get("name")
    return name if isinstance(name, str) and name else model.id


def _arguments(raw: str | None) -> dict[str, Any]:
    try:
        value = json.loads(raw or "{}")
    except ValueError:
        return {}
    return value if isinstance(value, dict) else {}
