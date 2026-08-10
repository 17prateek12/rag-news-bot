import asyncio

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services.cache_service import cache_service

router = APIRouter(tags=["health"])


@router.get("/health")
async def health(db: AsyncSession = Depends(get_db)):
    await db.execute(text("SELECT 1"))
    redis_ok = await asyncio.to_thread(cache_service.ping)
    return {
        "status": "ok",
        "service": "context-agent-backend",
        "redis": "ok" if redis_ok else "unavailable",
    }
