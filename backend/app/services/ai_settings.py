"""The language model of every AI feature: saved settings, model list, a test call, the model for the runtime."""

from typing import TYPE_CHECKING

from app.ai.base import AiError, ChatTurn, LanguageModel
from app.ai.factory import PROVIDERS, build_model, provider_info
from app.models import AiSettings
from app.schemas.ai import (
    AiModelList,
    AiModelOut,
    AiModelsRequest,
    AiProviderOut,
    AiSettingsOut,
    AiSettingsUpdate,
    AiTestResult,
)
from app.services import audit
from app.services.errors import InvalidInputError
from app.services.secret_box import SecretsUnreadableError, decrypt_value, encrypt_value

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

TEST_PROMPT = "Reply with the single word OK."


async def get_row(session: AsyncSession) -> AiSettings | None:
    return await session.get(AiSettings, 1)


def settings_out(row: AiSettings | None) -> AiSettingsOut:
    providers = [
        AiProviderOut(
            provider=info.provider,
            label=info.label,
            default_base_url=info.default_base_url,
            default_model=info.default_model,
            needs_base_url=info.needs_base_url,
            needs_api_key=info.needs_api_key,
        )
        for info in PROVIDERS
    ]
    if row is None:
        return AiSettingsOut(
            configured=False,
            provider=None,
            model=None,
            base_url=None,
            reasoning_effort=None,
            api_key_set=False,
            updated_at=None,
            providers=providers,
        )
    return AiSettingsOut(
        configured=True,
        provider=row.provider,
        model=row.model,
        base_url=row.base_url,
        reasoning_effort=row.reasoning_effort,
        api_key_set=row.api_key_encrypted is not None,
        updated_at=row.updated_at,
        providers=providers,
    )


async def save(session: AsyncSession, data: AiSettingsUpdate) -> AiSettingsOut:
    info = provider_info(data.provider)
    base_url = _clean_url(data.base_url)
    if info.needs_base_url and not base_url:
        raise InvalidInputError("A custom provider needs the base URL of its OpenAI-compatible API")
    row = await get_row(session)
    new_key = data.api_key.get_secret_value().strip() if data.api_key is not None else None
    same_provider = row is not None and row.provider == data.provider
    if new_key:
        key_encrypted: bytes | None = encrypt_value(new_key)
    elif data.api_key is None and same_provider:
        key_encrypted = row.api_key_encrypted if row else None
    else:
        key_encrypted = None
    if info.needs_api_key and key_encrypted is None:
        raise InvalidInputError(f"Enter the {info.label} API key")
    if row is None:
        row = AiSettings(id=1, provider=data.provider, model=data.model.strip())
        session.add(row)
    row.provider = data.provider
    row.model = data.model.strip()
    row.base_url = base_url
    row.reasoning_effort = data.reasoning_effort
    row.api_key_encrypted = key_encrypted
    await session.flush()
    await audit.record(
        session,
        "ai_settings.updated",
        "ai_settings",
        None,
        {
            "provider": str(data.provider),
            "model": row.model,
            "base_url": base_url,
            "reasoning_effort": data.reasoning_effort,
            "api_key_changed": bool(new_key),
        },
    )
    return settings_out(row)


async def list_models(session: AsyncSession, data: AiModelsRequest) -> AiModelList:
    row = await get_row(session)
    api_key = data.api_key.get_secret_value().strip() if data.api_key else ""
    if not api_key and row is not None and row.provider == data.provider:
        api_key = _key(row)
    info = provider_info(data.provider)
    if info.needs_api_key and not api_key:
        raise InvalidInputError(f"Enter the {info.label} API key to load its models")
    base_url = _clean_url(data.base_url)
    if info.needs_base_url and not base_url:
        raise InvalidInputError("Enter the base URL first")
    model = build_model(data.provider, api_key=api_key, model="-", base_url=base_url)
    try:
        options = await model.list_models()
    except AiError as exc:
        raise InvalidInputError(str(exc)) from exc
    if not options:
        raise InvalidInputError(f"{info.label} returned no models for this key")
    return AiModelList(
        models=[
            AiModelOut(
                id=option.id, name=option.name, efforts=list(option.efforts) if option.efforts is not None else None
            )
            for option in options
        ]
    )


async def test(session: AsyncSession) -> AiTestResult:
    model = await load_model(session)
    if model is None:
        return AiTestResult(ok=False, error="Save the AI settings first")
    try:
        reply = await model.reply(
            system="You check that the connection works.",
            history=[ChatTurn(role="user", text=TEST_PROMPT)],
            tools=[],
            execute=_no_tools,
        )
    except AiError as exc:
        return AiTestResult(ok=False, error=str(exc))
    return AiTestResult(ok=True, reply=reply[:500])


async def load_model(session: AsyncSession) -> LanguageModel | None:
    """The configured model, or ``None`` without settings or with a key that cannot be decrypted."""
    row = await get_row(session)
    if row is None:
        return None
    try:
        api_key = _key(row)
    except SecretsUnreadableError:
        return None
    return build_model(
        row.provider, api_key=api_key, model=row.model, base_url=row.base_url, effort=row.reasoning_effort
    )


def _key(row: AiSettings) -> str:
    return decrypt_value(row.api_key_encrypted) if row.api_key_encrypted else ""


def _clean_url(value: str | None) -> str | None:
    cleaned = (value or "").strip().rstrip("/")
    if cleaned and not cleaned.startswith(("http://", "https://")):
        raise InvalidInputError("The base URL must start with http:// or https://")
    return cleaned or None


async def _no_tools(name: str, arguments: dict) -> str:
    return ""
