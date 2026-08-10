import asyncio
import logging
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.repositories.chunk_repository import ChunkRepository
from app.repositories.embedding_service import embedding_service
from app.repositories.qdrant_repo import qdrant_repository
from app.services.cache_service import cache_service

logger = logging.getLogger(__name__)


def _hit_key(hit: dict[str, Any]) -> tuple[str, int]:
    return (
        str(hit.get("article_id", "")),
        int(hit.get("chunk_index") or 0),
    )


def reciprocal_rank_fusion(
    semantic_hits: list[dict[str, Any]],
    bm25_hits: list[dict[str, Any]],
    *,
    limit: int,
    k: int | None = None,
) -> list[dict[str, Any]]:
    rrf_k = k or settings.rrf_k
    fused_scores: dict[tuple[str, int], float] = {}
    hit_data: dict[tuple[str, int], dict[str, Any]] = {}

    for rank, hit in enumerate(semantic_hits):
        key = _hit_key(hit)
        fused_scores[key] = fused_scores.get(key, 0.0) + 1.0 / (rrf_k + rank + 1)
        existing = hit_data.get(key, {})
        hit_data[key] = {
            **existing,
            **hit,
            "semantic_score": hit.get("score"),
            "semantic_rank": rank + 1,
        }

    for rank, hit in enumerate(bm25_hits):
        key = _hit_key(hit)
        fused_scores[key] = fused_scores.get(key, 0.0) + 1.0 / (rrf_k + rank + 1)
        existing = hit_data.get(key, {})
        hit_data[key] = {
            **existing,
            **hit,
            "bm25_score": hit.get("bm25_score"),
            "bm25_rank": rank + 1,
        }

    ranked_keys = sorted(fused_scores.keys(), key=lambda key: fused_scores[key], reverse=True)[:limit]
    results: list[dict[str, Any]] = []
    for key in ranked_keys:
        merged = hit_data[key]
        merged["rrf_score"] = fused_scores[key]
        results.append(merged)
    return results


class HybridSearchService:
    def __init__(self, session: AsyncSession) -> None:
        self._chunk_repo = ChunkRepository(session)

    async def semantic_search(self, query: str, limit: int) -> list[dict[str, Any]]:
        vector = await asyncio.to_thread(embedding_service.embed_text, query)
        return await asyncio.to_thread(qdrant_repository.search, vector, limit)

    async def hybrid_search(self, query: str, limit: int | None = None) -> dict[str, Any]:
        result_limit = limit or settings.hybrid_result_limit

        cached = await asyncio.to_thread(cache_service.get_hybrid_search, query, result_limit)
        if cached is not None:
            cached["from_cache"] = True
            return cached

        semantic_limit = settings.hybrid_semantic_limit
        bm25_limit = settings.hybrid_bm25_limit

        logger.info(
            "Hybrid search query=%r limit=%s semantic_limit=%s bm25_limit=%s",
            query,
            result_limit,
            semantic_limit,
            bm25_limit,
        )

        vector = await asyncio.to_thread(embedding_service.embed_text, query)
        semantic_task = asyncio.to_thread(qdrant_repository.search, vector, semantic_limit)
        bm25_task = self._chunk_repo.search_bm25(query, bm25_limit)
        semantic_hits, bm25_hits = await asyncio.gather(semantic_task, bm25_task)

        fused = reciprocal_rank_fusion(
            semantic_hits,
            bm25_hits,
            limit=result_limit,
        )

        logger.info(
            "Hybrid search complete semantic=%s bm25=%s fused=%s",
            len(semantic_hits),
            len(bm25_hits),
            len(fused),
        )

        payload = {
            "query": query,
            "limit": result_limit,
            "semantic_count": len(semantic_hits),
            "bm25_count": len(bm25_hits),
            "results": fused,
            "from_cache": False,
        }
        await asyncio.to_thread(cache_service.set_hybrid_search, query, result_limit, payload)
        return payload
