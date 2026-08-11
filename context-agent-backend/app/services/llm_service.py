import logging

from app.config import settings
from app.core.exceptions import LLMError
from app.core.gemini_client import get_gemini_client

logger = logging.getLogger(__name__)


class LLMService:
    def generate_stream(self, prompt: str):
        logger.info("LLM generate_stream model=%s prompt_chars=%s", settings.gemini_model, len(prompt))
        try:
            client = get_gemini_client()
            response_stream = client.models.generate_content_stream(
                model=settings.gemini_model,
                contents=prompt,
            )
            for chunk in response_stream:
                text = chunk.text or ""
                if text:
                    yield text
        except Exception as exc:
            logger.exception("LLM streaming generation failed model=%s", settings.gemini_model)
            raise LLMError(
                "Vertex AI text streaming failed",
                details={"model": settings.gemini_model},
                cause=exc,
            ) from exc

    def generate(self, prompt: str) -> str:
        logger.info("LLM generate model=%s prompt_chars=%s", settings.gemini_model, len(prompt))
        try:
            client = get_gemini_client()
            response = client.models.generate_content(
                model=settings.gemini_model,
                contents=prompt,
            )
            text = response.text or ""
            logger.info("LLM generate complete response_chars=%s", len(text))
            return text.strip()
        except Exception as exc:
            logger.exception("LLM generation failed model=%s", settings.gemini_model)
            raise LLMError(
                "Vertex AI text generation failed",
                details={"model": settings.gemini_model},
                cause=exc,
            ) from exc


llm_service = LLMService()
