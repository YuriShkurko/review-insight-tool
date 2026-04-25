from __future__ import annotations

from app.llm.openai_compat import OpenAICompatProvider


def get_llm_provider() -> OpenAICompatProvider | None:
    """Return the configured LLM provider, or None when no API key is set (triggers mock path)."""
    from app.config import settings  # local import avoids circular deps at module load

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
