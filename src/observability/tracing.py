from __future__ import annotations

import logging

from src.config.settings import Settings

logger = logging.getLogger(__name__)

_instrumented = False


# Sends every LangChain/LangGraph LLM call (prompts, completions, latency,
# token usage) to Arize via OpenTelemetry auto-instrumentation. No-ops if
# ARIZE_API_KEY/ARIZE_SPACE_ID aren't set, the optional arize-otel /
# openinference packages aren't installed, or setup otherwise fails --
# tracing is observability, not a request-path dependency.
def setup_tracing(settings: Settings) -> None:
    global _instrumented
    if _instrumented or not settings.arize_enabled:
        return

    try:
        from arize.otel import register
        from openinference.instrumentation.langchain import LangChainInstrumentor
    except ImportError:
        logger.warning(
            "ARIZE_API_KEY/ARIZE_SPACE_ID are set but arize-otel and "
            "openinference-instrumentation-langchain aren't installed; Arize "
            "tracing disabled. Run: pip install -r requirements.txt"
        )
        return

    try:
        tracer_provider = register(
            space_id=settings.arize_space_id,
            api_key=settings.arize_api_key,
            project_name=settings.arize_project_name,
        )
        LangChainInstrumentor().instrument(tracer_provider=tracer_provider)
    except Exception:
        logger.exception("Failed to initialize Arize tracing; continuing without it")
        return

    _instrumented = True
    logger.info("Arize tracing enabled (project=%s)", settings.arize_project_name)
