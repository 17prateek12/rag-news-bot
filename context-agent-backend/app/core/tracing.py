import functools
import logging
import os
from typing import Any, Callable

from app.config import settings

logger = logging.getLogger(__name__)

# Configure environment variables if LangSmith tracing is enabled
if settings.langchain_tracing_v2 and settings.langchain_api_key:
    os.environ["LANGCHAIN_TRACING_V2"] = "true"
    os.environ["LANGCHAIN_API_KEY"] = settings.langchain_api_key
    os.environ["LANGCHAIN_PROJECT"] = settings.langchain_project
    os.environ["LANGCHAIN_ENDPOINT"] = settings.langchain_endpoint
    logger.info("LangSmith tracing enabled project=%s", settings.langchain_project)


def traceable(
    name: str | None = None,
    run_type: str = "chain",
    metadata: dict[str, Any] | None = None,
    tags: list[str] | None = None,
) -> Callable:
    """Safe decorator for LangSmith tracing.

    When LANGCHAIN_TRACING_V2 is active, delegates to langsmith.traceable.
    When disabled, returns the original function unmodified with zero overhead.
    """
    if not settings.langchain_tracing_v2:
        def noop_decorator(fn: Callable) -> Callable:
            return fn
        return noop_decorator

    try:
        from langsmith import traceable as ls_traceable

        return ls_traceable(
            name=name,
            run_type=run_type,
            metadata=metadata,
            tags=tags,
        )
    except ImportError:
        logger.debug("langsmith not installed, tracing disabled")
        def noop_decorator(fn: Callable) -> Callable:
            return fn
        return noop_decorator
