import asyncio
import logging

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.database import get_db
from app.repositories.embedding_service import embedding_service
from app.repositories.qdrant_repo import qdrant_repository
from app.schemas.search import HybridSearchResponse, SearchHit
from app.services.hybrid_search_service import HybridSearchService
from app.services.reranker_service import reranker_service
from app.services.search_relevance import filter_hits_by_topic

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
    candidate_limit = settings.rerank_candidate_limit if rerank else limit
    if topic_match:
        candidate_limit = max(candidate_limit, 40)

    payload = await service.hybrid_search(q, limit=candidate_limit)
    results = payload["results"]
    rerank_to = candidate_limit if topic_match else limit
    if rerank and settings.reranker_enabled and len(results) > 1:
        results = await asyncio.to_thread(reranker_service.rerank, q, results, rerank_to)

    if topic_match:
        results = filter_hits_by_topic(q, results)

    results = results[:limit]
    return HybridSearchResponse(
        query=payload["query"],
        limit=limit,
        semantic_count=payload["semantic_count"],
        bm25_count=payload["bm25_count"],
        results=[SearchHit(**hit) for hit in results],
    )
