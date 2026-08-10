import logging
from typing import Any

from app.config import settings

logger = logging.getLogger(__name__)

_model = None


def _get_model():
    global _model
    if _model is None:
        from sentence_transformers import CrossEncoder

        logger.info("Loading reranker model=%s", settings.reranker_model)
        _model = CrossEncoder(settings.reranker_model)
    return _model


class RerankerService:
    def rerank(self, query: str, hits: list[dict[str, Any]], top_k: int) -> list[dict[str, Any]]:
        if not hits:
            return []
        if len(hits) <= top_k:
            return hits

        pairs = [(query, hit.get("chunk") or hit.get("title") or "") for hit in hits]
        scores = _get_model().predict(pairs)

        scored: list[dict[str, Any]] = []
        for hit, score in zip(hits, scores, strict=True):
            enriched = {**hit, "rerank_score": float(score)}
            scored.append(enriched)

        scored.sort(key=lambda item: item["rerank_score"], reverse=True)
        top = scored[:top_k]
        logger.info(
            "Reranked candidates=%s top_k=%s best_score=%.4f worst_score=%.4f",
            len(hits),
            top_k,
            top[0]["rerank_score"],
            top[-1]["rerank_score"],
        )
        return top


reranker_service = RerankerService()
