"""Claude through the official ``anthropic`` SDK, Messages API with a manual tool loop.

The loop appends each response's content unchanged (thinking blocks included) and
never edits earlier messages, so preserved thinking stays valid within a turn.
Earlier turns are replayed as plain text without thinking blocks, which the API
accepts. Models that support it get the server-side refusal fallback. The admin's
reasoning level goes to ``output_config.effort``; without one the API's default for
the model applies. The model list reads each model's effort levels from the Models API.
"""

from typing import Any

import anthropic
from anthropic import AsyncAnthropic

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

MAX_TOKENS = 16000
FALLBACK_BETA = "server-side-fallback-2026-07-01"
# Models that accept ``fallbacks: "default"`` (a refused request is re-run on a fallback model).
FALLBACK_MODELS = frozenset(
    {"claude-fable-5-2", "claude-fable-5-1", "claude-opus-5-5", "claude-opus-5", "claude-sonnet-5-5"}
)
REFUSAL_TEXT = "I can't help with that request."


class AnthropicModel:
    def __init__(
        self, *, api_key: str, model: str, base_url: str | None = None, effort: AiReasoningEffort | None = None
    ) -> None:
        self._model = model
        self._effort = effort
        self._client = AsyncAnthropic(
            api_key=api_key, base_url=base_url or None, timeout=REQUEST_TIMEOUT_SECONDS, max_retries=2
        )

    async def reply(self, *, system: str, history: list[ChatTurn], tools: list[ToolSpec], execute: ToolExecutor) -> str:
        messages: list[dict[str, Any]] = [{"role": turn.role, "content": turn.text} for turn in history]
        tool_defs = [{"name": t.name, "description": t.description, "input_schema": t.parameters} for t in tools]
        for _ in range(MAX_TOOL_ROUNDS):
            response = await self._create(system, messages, tool_defs)
            if response.stop_reason == "refusal":
                return REFUSAL_TEXT
            messages.append({"role": "assistant", "content": response.content})
            if response.stop_reason == "pause_turn":
                continue
            calls = [block for block in response.content if block.type == "tool_use"]
            if not calls:
                return _text(response.content)
            results = []
            for call in calls:
                output, is_error = await run_tool(execute, call.name, dict(call.input or {}))
                results.append({"type": "tool_result", "tool_use_id": call.id, "content": output, "is_error": is_error})
            messages.append({"role": "user", "content": results})  # all results of one response in one message
        raise AiError(f"The model called tools more than {MAX_TOOL_ROUNDS} times in one answer")

    async def list_models(self) -> list[ModelOption]:
        try:
            models = [model async for model in self._client.models.list(limit=100)]
        except anthropic.APIError as exc:
            raise _error(exc) from exc
        return [
            ModelOption(id=model.id, name=model.display_name or model.id, efforts=_efforts(model.capabilities))
            for model in models
            if model.lifecycle != "retired"
        ]

    async def _create(self, system: str, messages: list[dict[str, Any]], tools: list[dict[str, Any]]) -> Any:
        params: dict[str, Any] = {
            "model": self._model,
            "max_tokens": MAX_TOKENS,
            "system": system,
            "messages": messages,
        }
        if tools:
            params["tools"] = tools
        if self._effort:
            params["extra_body"] = {"output_config": {"effort": str(self._effort)}}
        try:
            if self._model in FALLBACK_MODELS:
                return await self._client.beta.messages.create(**params, betas=[FALLBACK_BETA], fallbacks="default")
            return await self._client.messages.create(**params)
        except anthropic.APIError as exc:
            raise _error(exc) from exc


def _efforts(capabilities: Any) -> tuple[AiReasoningEffort, ...]:
    """Effort levels the Models API marks as supported; empty for a model without ``effort``."""
    effort = getattr(capabilities, "effort", None)
    if effort is None or not effort.supported:
        return ()
    return tuple(
        level for level in AiReasoningEffort if getattr(getattr(effort, level.value, None), "supported", False)
    )


def _text(content: list[Any]) -> str:
    return "\n".join(block.text for block in content if block.type == "text").strip()


def _error(exc: anthropic.APIError) -> AiError:
    if isinstance(exc, anthropic.AuthenticationError):
        return AiError("Anthropic rejected the API key")
    if isinstance(exc, anthropic.PermissionDeniedError):
        return AiError("The Anthropic API key has no access to this model or feature")
    if isinstance(exc, anthropic.NotFoundError):
        return AiError("Anthropic does not know this model. Pick one from the list")
    if isinstance(exc, anthropic.RateLimitError):
        return AiError("Anthropic rate limit reached. Try again in a minute")
    if isinstance(exc, anthropic.BadRequestError):
        return AiError(f"Anthropic refused the request: {exc.message}")
    if isinstance(exc, anthropic.APIStatusError):
        return AiError(f"Anthropic error {exc.status_code}: {exc.message}")
    if isinstance(exc, anthropic.APIConnectionError):
        return AiError("Cannot reach the Anthropic API")
    return AiError(f"Anthropic error: {exc}")
