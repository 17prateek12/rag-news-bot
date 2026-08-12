import asyncio
import logging

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.database import get_db
from app.repositories.chunk_repository import ChunkRepository
from app.repositories.embedding_service import embedding_service
from app.repositories.qdrant_repo import qdrant_repository
from app.schemas.search import HybridSearchResponse, SearchHit
from app.services.cache_service import cache_service
from app.services.hybrid_search_service import HybridSearchService
from app.services.reranker_service import reranker_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/search", tags=["search"])


@router.get("")
async def semantic_search(
    q: str = Query(min_length=1),
    limit: int = Query(default=6, ge=1, le=20),
):
    logger.info("Semantic search query=%r limit=%s", q, limit)
    vector = await asyncio.to_thread(embedding_service.embed_text, q)
    results = await asyncio.to_thread(qdrant_repository.search, vector, limit)
    return {"query": q, "limit": limit, "mode": "semantic", "results": results}


@router.get("/hybrid", response_model=HybridSearchResponse)
async def hybrid_search(
    q: str = Query(min_length=1),
    limit: int = Query(default=6, ge=1, le=20),
    rerank: bool = Query(default=False),
    topic_match: bool = Query(default=False),
    db: AsyncSession = Depends(get_db),
):
    service = HybridSearchService(db)
    
    # Enforce rerank if topic_match is True
    if topic_match:
        rerank = True
        
    candidate_limit = settings.rerank_candidate_limit if rerank else limit
    if topic_match:
        candidate_limit = max(candidate_limit, 40)

    payload = await service.hybrid_search(q, limit=candidate_limit)
    results = payload["results"]
    rerank_to = candidate_limit if topic_match else limit
    if rerank and settings.reranker_enabled and len(results) > 1:
        results = await asyncio.to_thread(reranker_service.rerank, q, results, rerank_to)

    if topic_match:
        results = [h for h in results if h.get("rerank_score", 0.0) >= settings.relevance_score_floor]

    results = results[:limit]
    return HybridSearchResponse(
        query=payload["query"],
        limit=limit,
        semantic_count=payload["semantic_count"],
        bm25_count=payload["bm25_count"],
        results=[SearchHit(**hit) for hit in results],
    )


@router.get("/bm25", response_model=HybridSearchResponse)
async def bm25_search(
    q: str = Query(min_length=1),
    limit: int = Query(default=6, ge=1, le=20),
    db: AsyncSession = Depends(get_db),
):
    logger.info("BM25 search query=%r limit=%s", q, limit)
    cached = await asyncio.to_thread(cache_service.get_bm25_search, q, limit)
    if cached is not None:
        return HybridSearchResponse(
            query=q,
            limit=limit,
            semantic_count=0,
            bm25_count=cached["bm25_count"],
            results=[SearchHit(**hit) for hit in cached["results"]],
        )

    repo = ChunkRepository(db)
    hits = await repo.search_bm25(q, limit)

    payload = {
        "results": hits,
        "bm25_count": len(hits),
    }
    await asyncio.to_thread(cache_service.set_bm25_search, q, limit, payload)

    return HybridSearchResponse(
        query=q,
        limit=limit,
        semantic_count=0,
        bm25_count=len(hits),
        results=[SearchHit(**hit) for hit in hits],
    )
