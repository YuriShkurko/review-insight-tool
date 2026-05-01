from __future__ import annotations

from app.llm.base import LLMProvider
from app.llm.openai_compat import OpenAICompatProvider
from app.llm.scripted import ScriptedProvider, get_scripted_provider


def get_llm_provider() -> LLMProvider | None:
    """Return the configured LLM provider, or None when no API key is set (triggers mock path)."""
    from app.config import settings  # local import avoids circular deps at module load

    if settings.LLM_PROVIDER == "scripted":
        # Scripted is a deterministic test provider. Never auto-enabled in
        # production: the operator has to set both LLM_PROVIDER=scripted AND
        # TESTING=true for it to be selected. This is the safety rail.
        if not settings.TESTING:
            return None
        provider: ScriptedProvider = get_scripted_provider()
        if settings.AGENT_SCRIPT_PATH and provider.remaining == 0:
            provider.load_from_path(settings.AGENT_SCRIPT_PATH)
        return provider

    if settings.LLM_PROVIDER == "openrouter":
        if not settings.OPENROUTER_API_KEY:
            return None
        return OpenAICompatProvider(
            api_key=settings.OPENROUTER_API_KEY,
            default_model=settings.LLM_MODEL,
            base_url="https://openrouter.ai/api/v1",
        )

    # Default: openai
    if not settings.OPENAI_API_KEY:
        return None
    return OpenAICompatProvider(
        api_key=settings.OPENAI_API_KEY,
        default_model=settings.LLM_MODEL,
    )
