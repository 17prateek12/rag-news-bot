import logging
import threading
from typing import Any

from app.config import settings

logger = logging.getLogger(__name__)

_model = None
_model_lock = threading.Lock()


def _get_model():
    global _model
    if _model is None:
        with _model_lock:
            if _model is None:
                from sentence_transformers import CrossEncoder

                logger.info("Loading reranker model=%s", settings.reranker_model)
                _model = CrossEncoder(settings.reranker_model)
    return _model


class RerankerService:
    def rerank(self, query: str, hits: list[dict[str, Any]], top_k: int) -> list[dict[str, Any]]:
        if not hits:
            return []

        pairs = [(query, hit.get("chunk") or hit.get("title") or "") for hit in hits]
        scores = _get_model().predict(pairs)

        scored: list[dict[str, Any]] = []
        from datetime import datetime, timezone
        from app.services.web_fallback_service import _parse_publish_date

        query_lower = query.lower()
        has_former_query = any(w in query_lower for w in ["former", "previous", "ex-", "past", "history", "old", "predecessor"])

        for hit, score in zip(hits, scores, strict=True):
            adjusted_score = float(score)

            # 1. Recency bonus (up to +0.5 for brand new articles)
            ds = hit.get("publish_date")
            if ds:
                parsed_dt = _parse_publish_date(ds)
                if parsed_dt:
                    age_days = (datetime.now(timezone.utc) - parsed_dt).total_seconds() / (3600 * 24)
                    if age_days >= 0:
                        recency_bonus = 0.5 / (1.0 + age_days)
                        adjusted_score += recency_bonus

            # 2. "Former" state demotion (penalize if query asks about current state but chunk is about former state)
            if not has_former_query:
                chunk_text = (hit.get("chunk") or hit.get("title") or "").lower()
                if any(w in chunk_text for w in ["former", "previous", "ex-chairman", "ex-president", "ex-chief", "predecessor"]):
                    adjusted_score -= 2.0  # Significant penalty

            enriched = {**hit, "rerank_score": adjusted_score}
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
