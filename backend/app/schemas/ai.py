from datetime import datetime

from pydantic import BaseModel, Field, SecretStr

from app.models.enums import AiProvider, AiReasoningEffort


class AiProviderOut(BaseModel):
    provider: AiProvider
    label: str
    default_base_url: str | None
    default_model: str | None
    needs_base_url: bool = Field(description="The base URL is required (custom endpoint)")
    needs_api_key: bool


class AiSettingsOut(BaseModel):
    configured: bool = Field(description="A model is saved; the agents can answer")
    provider: AiProvider | None
    model: str | None
    base_url: str | None
    reasoning_effort: AiReasoningEffort | None = Field(description="Null: the provider's default for the model")
    api_key_set: bool
    updated_at: datetime | None
    providers: list[AiProviderOut]


class AiSettingsUpdate(BaseModel):
    """``api_key`` null keeps the saved key (only when the provider stays the same)."""

    provider: AiProvider
    model: str = Field(min_length=1, max_length=200)
    base_url: str | None = Field(default=None, max_length=2000)
    api_key: SecretStr | None = Field(default=None, max_length=1000)
    reasoning_effort: AiReasoningEffort | None = None


class AiModelsRequest(BaseModel):
    """Lists models before saving. Without ``api_key`` the saved key of the same provider is used."""

    provider: AiProvider
    base_url: str | None = Field(default=None, max_length=2000)
    api_key: SecretStr | None = Field(default=None, max_length=1000)


class AiModelOut(BaseModel):
    id: str
    name: str = Field(description="Display name; the id when the provider sends none")
    efforts: list[AiReasoningEffort] | None = Field(
        description="Reasoning levels the model takes; empty: none; null: the provider does not say"
    )


class AiModelList(BaseModel):
    models: list[AiModelOut]


class AiTestResult(BaseModel):
    ok: bool
    reply: str | None = None
    error: str | None = None
