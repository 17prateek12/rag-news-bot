import logging

import httpx
from google import genai

from app.config import settings
from app.core.exceptions import ConfigurationError, EmbeddingError, FetchError

logger = logging.getLogger(__name__)

_client: genai.Client | None = None


def get_gemini_client() -> genai.Client:
    """Return a google-genai client authenticated via Vertex AI."""
    global _client
    if _client is None:
        if not settings.gcp_project:
            raise ConfigurationError(
                "GCP_PROJECT is not set",
                details={
                    "hint": "Set GCP_PROJECT and GCP_LOCATION in .env",
                    "auth": "Use `gcloud auth application-default login` or GOOGLE_APPLICATION_CREDENTIALS",
                },
            )
        logger.info(
            "Initializing Vertex AI client project=%s location=%s",
            settings.gcp_project,
            settings.gcp_location,
        )
        try:
            _client = genai.Client(
                vertexai=True,
                project=settings.gcp_project,
                location=settings.gcp_location,
            )
        except Exception as exc:
            raise ConfigurationError(
                "Failed to initialize Vertex AI client",
                details={"project": settings.gcp_project, "location": settings.gcp_location},
                cause=exc,
            ) from exc
    return _client
