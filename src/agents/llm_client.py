from __future__ import annotations

from langchain_groq import ChatGroq

from src.config.settings import Settings


# Builds a ChatGroq client from Settings (API key, model, base URL, temperature,
# max tokens, timeout) for use by the graph nodes and agents.
def build_llm(settings: Settings) -> ChatGroq:
    return ChatGroq(
        api_key=settings.groq_api_key,
        model=settings.groq_model,
        base_url=settings.groq_base_url,
        temperature=settings.llm_temperature,
        max_tokens=settings.llm_max_tokens,
        timeout=settings.llm_timeout_seconds,
    )
