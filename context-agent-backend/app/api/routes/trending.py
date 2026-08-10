import asyncio

from fastapi import APIRouter, Query

from app.schemas.trending import TrendingQuery, TrendingResponse
from app.services.cache_service import cache_service

router = APIRouter(prefix="/trending", tags=["trending"])


@router.get("", response_model=TrendingResponse)
async def get_trending(
    limit: int = Query(default=10, ge=1, le=50),
):
    items = await asyncio.to_thread(cache_service.get_trending, limit)
    return TrendingResponse(
        queries=[
            TrendingQuery(topic=item["topic"], query=item["query"], count=item["count"])
            for item in items
        ],
    )
