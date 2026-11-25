# open-revoke/backend/app/ai/

Language models for the agents (the Slack agent): one `LanguageModel` protocol, one module per provider; `factory.build_model` picks one from the panel settings (`services/ai_settings.py`). `reply` runs the whole tool loop of one turn.

- `base.py`: `LanguageModel` protocol (`reply`, `list_models` returning `ModelOption`: id, name, reasoning levels or `None` when unknown), `ToolSpec`, `ChatTurn`, `ToolExecutor`, `ToolError` (goes back to the model as an error result), `AiError` (safe to show an admin), `run_tool`, limits `MAX_TOOL_ROUNDS` (8) and `REQUEST_TIMEOUT_SECONDS`.
- `factory.py`: `PROVIDERS` catalog (`ProviderInfo`: label, default URL and model, needs key or URL), `provider_info`, `build_model(provider, api_key, model, base_url, effort)`.
- `anthropic_model.py`: `AnthropicModel`, Messages API with a manual tool loop; keeps thinking blocks within a turn, refusal fallback for `FALLBACK_MODELS`; effort as `output_config.effort`; model levels from the Models API `capabilities`.
- `openai_compatible.py`: `OpenAiCompatibleModel`, Chat Completions for OpenAI, OpenRouter and any compatible endpoint (key optional); `reasoning_effort` (OpenRouter: `reasoning.effort`); OpenRouter `supported_parameters` tell which models reason; OpenAI list drops non-chat models.
- `__init__.py`: docstring only, overview of providers.
