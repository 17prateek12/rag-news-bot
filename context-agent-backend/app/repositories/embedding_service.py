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
        if not texts:
            return []

        logger.info("Embedding batch size=%s", len(texts))
        cache_keys = [f"embed:{content_hash(text)}" for text in texts]
        cached_values = [None] * len(texts)

        try:
            redis_client = get_sync_redis()
            cached_raw = redis_client.mget(cache_keys)
            for idx, cached in enumerate(cached_raw):
                if cached:
                    cached_values[idx] = [float(value) for value in cached.split(",")]
        except Exception as exc:
            logger.warning("Redis cache MGET failed: %s", exc)

        uncached_indices = [idx for idx, val in enumerate(cached_values) if val is None]

        if uncached_indices:
            uncached_texts = [texts[idx] for idx in uncached_indices]
            logger.info("Requesting batch embedding from Vertex AI count=%s", len(uncached_texts))
            try:
                client = get_gemini_client()
                response = client.models.embed_content(
                    model=settings.embedding_model,
                    contents=uncached_texts,
                )

                if len(response.embeddings) != len(uncached_texts):
                    raise EmbeddingError(
                        "Vertex AI batch embedding returned mismatched count",
                        details={"expected": len(uncached_texts), "got": len(response.embeddings)},
                    )

                for u_idx, embedding in enumerate(response.embeddings):
                    original_idx = uncached_indices[u_idx]
                    values = list(embedding.values)
                    cached_values[original_idx] = values

                    try:
                        redis_client.setex(
                            cache_keys[original_idx],
                            60 * 60 * 24 * 7,  # 7 days
                            ",".join(str(value) for value in values),
                        )
                    except Exception:
                        pass
            except Exception as exc:
                logger.warning("Vertex AI batch embedding failed, falling back to sequential: %s", exc)
                for idx in uncached_indices:
                    cached_values[idx] = self.embed_text(texts[idx])

        return cached_values


embedding_service = EmbeddingService()
