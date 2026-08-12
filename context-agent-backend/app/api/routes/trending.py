import asyncio
import logging
import uuid
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.trending import TrendingEntity
from app.schemas.search import HybridSearchResponse, SearchHit
from app.schemas.trending import TrendingResponse, TrendingEntityResponse
from app.services.trending_service import trending_service
from app.services.hybrid_search_service import HybridSearchService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/trending", tags=["trending"])


@router.get("", response_model=TrendingResponse)
async def get_trending(
    limit: int = Query(default=10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
):
    news_items = await trending_service.get_trending_news(db, limit)
    search_items = await trending_service.get_trending_searches(db, limit)

    return TrendingResponse(
        trending_news=[
            TrendingEntityResponse(**item)
            for item in news_items
        ],
        trending_searches=[
            TrendingEntityResponse(**item)
            for item in search_items
        ],
    )


@router.get("/entities/{entity_id}/articles", response_model=HybridSearchResponse)
async def get_entity_articles(
    entity_id: str,
    db: AsyncSession = Depends(get_db),
):
    try:
        entity_uuid = uuid.UUID(entity_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid entity ID format")

    stmt = select(TrendingEntity).filter(TrendingEntity.id == entity_uuid)
    result = await db.execute(stmt)
    entity = result.scalars().first()
    if not entity:
        raise HTTPException(status_code=404, detail="Entity not found")

    seen_urls = set()
    results = []

    # 1. Fetch pre-linked articles from database
    if entity.articles:
        # Order them by publication date descending
        sorted_articles = sorted(entity.articles, key=lambda a: a.published_at, reverse=True)
        for art in sorted_articles:
            norm_url = art.url.rstrip("/")
            if norm_url in seen_urls:
                continue
            seen_urls.add(norm_url)
            results.append(
                SearchHit(
                    article_id=str(art.id),
                    title=art.title,
                    chunk=art.summary or "",
                    source=art.source,
                    url=art.url,
                    publish_date=art.published_at.isoformat() if art.published_at else None,
                    categories=art.categories,
                )
            )

    # 2. Fetch real-time web search fallback results (if enabled)
    from app.services.web_fallback_service import web_fallback_service
    if web_fallback_service.is_enabled():
        try:
            loop = asyncio.get_running_loop()
            def fetch_fallback():
                return web_fallback_service.search(entity.canonical_name, limit=12)
            fallback_hits = await loop.run_in_executor(None, fetch_fallback)
            
            for hit in fallback_hits:
                url = hit.get("url") or ""
                norm_url = url.rstrip("/")
                if norm_url in seen_urls:
                    continue
                seen_urls.add(norm_url)
                
                results.append(
                    SearchHit(
                        article_id=hit.get("article_id") or f"web:{uuid.uuid4()}",
                        title=hit.get("title") or "Untitled",
                        chunk=hit.get("chunk") or "",
                        source=hit.get("source") or "web",
                        url=url,
                        publish_date=hit.get("publish_date"),
                        categories=[]
                    )
                )
        except Exception as exc:
            logger.warning("Web fallback search failed for trending entity %s: %s", entity.canonical_name, exc)

    # 3. If still empty, fall back to local hybrid search (as a safety measure)
    if not results:
        search_service = HybridSearchService(db)
        search_res = await search_service.hybrid_search(entity.canonical_name, limit=12)
        return search_res

    return HybridSearchResponse(
        query=entity.canonical_name,
        limit=len(results),
        semantic_count=0,
        bm25_count=0,
        results=results,
    )
