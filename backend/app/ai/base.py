"""Types shared by the language model providers."""

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Literal, Protocol

if TYPE_CHECKING:
    from app.models.enums import AiReasoningEffort

# Tool calls in one turn before the agent gives up: a loop that never ends costs money.
MAX_TOOL_ROUNDS = 8
REQUEST_TIMEOUT_SECONDS = 120.0


@dataclass(frozen=True)
class ToolSpec:
    """A function the model may call. ``parameters`` is a JSON Schema object."""

    name: str
    description: str
    parameters: dict[str, Any]


@dataclass(frozen=True)
class ChatTurn:
    """Earlier text of the conversation. Tool calls of earlier turns are not replayed."""

    role: Literal["user", "assistant"]
    text: str


@dataclass(frozen=True)
class ModelOption:
    """A model the key can use. ``efforts`` are the reasoning levels it takes; ``None`` when the API does not say."""

    id: str
    name: str
    efforts: tuple[AiReasoningEffort, ...] | None


class ToolError(Exception):
    """A tool could not do what the model asked; the message goes back to the model as an error result."""


class AiError(Exception):
    """The provider failed: bad key, unknown model, network, rate limit. The message is safe to show an admin."""


# Runs one tool call: name and parsed arguments in, text for the model out. Raises ToolError.
ToolExecutor = Callable[[str, dict[str, Any]], Awaitable[str]]


class LanguageModel(Protocol):
    async def reply(self, *, system: str, history: list[ChatTurn], tools: list[ToolSpec], execute: ToolExecutor) -> str:
        """Answer the last user turn of ``history``, calling tools as the model asks. Raises AiError."""
        ...

    async def list_models(self) -> list[ModelOption]:
        """Models the key can use, with their reasoning levels when the API reports them. Raises AiError."""
        ...


async def run_tool(execute: ToolExecutor, name: str, arguments: dict[str, Any]) -> tuple[str, bool]:
    """Result text and whether it is an error. Unexpected exceptions propagate."""
    try:
        return await execute(name, arguments), False
    except ToolError as exc:
        return str(exc), True
