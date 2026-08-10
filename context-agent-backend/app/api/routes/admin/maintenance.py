import asyncio
import logging
import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.admin_auth import get_current_admin
from app.core.bootstrap_data import CATEGORIES
from app.core.database import get_db
from app.models.admin import Admin
from app.models.article import Article
from app.models.category import Category
from app.models.rss_source import RssSource
from app.repositories.chunk_repository import ChunkRepository
from app.repositories.qdrant_repo import qdrant_repository
from app.services.retention_service import RetentionService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["admin-maintenance"])


@router.post("/maintenance/cleanup")
async def cleanup_old_articles(
    _: Admin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await RetentionService(db).cleanup_old_articles()
    return result.to_dict()


@router.get("/health/feed-coverage")
async def feed_coverage(
    _: Admin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    categories = list((await db.execute(select(Category))).scalars().all())
    feeds = list((await db.execute(select(RssSource).where(RssSource.is_active.is_(True)))).scalars().all())

    covered_ids = {feed.category_id for feed in feeds}
    missing = [
        {"id": cat.id, "name": cat.name}
        for cat in categories
        if cat.id not in covered_ids
    ]

    bootstrap_missing = [name for name in CATEGORIES if name not in {cat.name for cat in categories}]

    return {
        "total_categories": len(categories),
        "total_active_feeds": len(feeds),
        "categories_without_active_feeds": missing,
        "bootstrap_categories_not_in_db": bootstrap_missing,
    }


@router.post("/maintenance/backfill-chunks")
async def backfill_chunks(
    _: Admin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Sync Postgres BM25 chunks from existing Qdrant vectors (one-time after Step 5 migration)."""
    articles = list((await db.execute(select(Article))).scalars().all())
    chunk_repo = ChunkRepository(db)
    backfilled = 0
    skipped = 0

    for article in articles:
        qdrant_chunks = await asyncio.to_thread(
            qdrant_repository.list_chunks_for_article,
            article.id,
        )
        if not qdrant_chunks:
            skipped += 1
            continue

        qdrant_chunks.sort(key=lambda item: item.get("chunk_index") or 0)
        texts = [item["chunk"] for item in qdrant_chunks if item.get("chunk")]
        point_ids = [
            uuid.UUID(item["point_id"])
            for item in qdrant_chunks
            if item.get("point_id")
        ]
        if not texts:
            skipped += 1
            continue

        await chunk_repo.replace_for_article(article, texts, point_ids)
        backfilled += 1

    total_chunks = await chunk_repo.count_all()
    logger.info("Backfill complete articles=%s skipped=%s total_chunks=%s", backfilled, skipped, total_chunks)
    return {
        "articles_backfilled": backfilled,
        "articles_skipped": skipped,
        "postgres_chunk_count": total_chunks,
    }
