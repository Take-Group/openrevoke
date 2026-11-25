"""Provider catalog for the panel and the model built from the saved settings."""

from dataclasses import dataclass
from typing import TYPE_CHECKING

from app.ai.anthropic_model import AnthropicModel
from app.ai.openai_compatible import OpenAiCompatibleModel
from app.models.enums import AiProvider, AiReasoningEffort

if TYPE_CHECKING:
    from app.ai.base import LanguageModel

OPENROUTER_URL = "https://openrouter.ai/api/v1"


@dataclass(frozen=True)
class ProviderInfo:
    provider: AiProvider
    label: str
    default_base_url: str | None
    default_model: str | None
    needs_base_url: bool
    needs_api_key: bool


PROVIDERS: tuple[ProviderInfo, ...] = (
    ProviderInfo(AiProvider.ANTHROPIC, "Anthropic", None, "claude-opus-5-5", False, True),
    ProviderInfo(AiProvider.OPENAI, "OpenAI", None, None, False, True),
    ProviderInfo(AiProvider.OPENROUTER, "OpenRouter", OPENROUTER_URL, None, False, True),
    # Any OpenAI-compatible endpoint (vLLM, Ollama, LiteLLM, Azure gateway); local ones may take no key.
    ProviderInfo(AiProvider.CUSTOM, "Custom (OpenAI-compatible)", None, None, True, False),
)


def provider_info(provider: AiProvider) -> ProviderInfo:
    return next(info for info in PROVIDERS if info.provider == provider)


def build_model(
    provider: AiProvider,
    *,
    api_key: str,
    model: str,
    base_url: str | None,
    effort: AiReasoningEffort | None = None,
) -> LanguageModel:
    if provider == AiProvider.ANTHROPIC:
        return AnthropicModel(api_key=api_key, model=model, base_url=base_url, effort=effort)
    if provider == AiProvider.OPENROUTER:
        return OpenAiCompatibleModel(
            api_key=api_key,
            model=model,
            base_url=base_url or OPENROUTER_URL,
            label="OpenRouter",
            headers={"X-Title": "Open Revoke"},
            effort=effort,
            openrouter=True,
        )
    if provider == AiProvider.OPENAI:
        return OpenAiCompatibleModel(api_key=api_key, model=model, base_url=base_url, effort=effort, chat_only=True)
    return OpenAiCompatibleModel(api_key=api_key, model=model, base_url=base_url, label="The endpoint", effort=effort)
