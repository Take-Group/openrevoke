"""Language models for the agents: one interface, providers in their own modules.

``LanguageModel.reply`` runs the whole tool loop of one turn and returns the
text to show. Anthropic goes through the official ``anthropic`` SDK; OpenAI,
OpenRouter and any OpenAI-compatible endpoint go through the ``openai`` SDK
(``openai_compatible.py``). ``factory.build_model`` picks one from the panel
settings (``app.services.ai_settings``).
"""
