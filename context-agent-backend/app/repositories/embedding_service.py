import logging

from app.config import settings
from app.core.exceptions import EmbeddingError
from app.core.gemini_client import get_gemini_client
from app.core.redis_client import get_sync_redis
from app.ingestion.hasher import content_hash

logger = logging.getLogger(__name__)


class EmbeddingService:
    def embed_text(self, text: str) -> list[float]:
        cache_key = f"embed:{content_hash(text)}"
        try:
            redis_client = get_sync_redis()
            cached = redis_client.get(cache_key)
            if cached:
                logger.debug("Embedding cache hit hash=%s", cache_key[-12:])
                return [float(value) for value in cached.split(",")]
        except Exception as exc:
            logger.warning("Redis cache read failed, continuing without cache: %s", exc)

        logger.debug("Embedding text via Vertex AI model=%s chars=%s", settings.embedding_model, len(text))
        try:
            client = get_gemini_client()
            response = client.models.embed_content(
                model=settings.embedding_model,
                contents=text,
            )
            values = list(response.embeddings[0].values)
        except Exception as exc:
            logger.exception("Vertex AI embedding failed model=%s", settings.embedding_model)
            raise EmbeddingError(
                "Vertex AI embedding request failed",
                details={"model": settings.embedding_model, "text_length": len(text)},
                cause=exc,
            ) from exc

        try:
            redis_client.setex(
                cache_key,
                60 * 60 * 24 * 7,
                ",".join(str(value) for value in values),
            )
        except Exception as exc:
            logger.warning("Redis cache write failed: %s", exc)

        logger.debug("Embedding success dims=%s", len(values))
        return values

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        logger.info("Embedding batch size=%s", len(texts))
        return [self.embed_text(text) for text in texts]


embedding_service = EmbeddingService()
