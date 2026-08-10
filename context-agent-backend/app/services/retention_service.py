import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.ingestion.vector_loader import VectorLoader
from app.models.article import Article
from app.services.cache_service import cache_service

logger = logging.getLogger(__name__)


@dataclass
class RetentionCleanupResult:
    deleted_count: int
    vectors_removed: int
    cutoff: datetime
    retention_days: int

    def to_dict(self) -> dict:
        return {
            "deleted_count": self.deleted_count,
            "vectors_removed": self.vectors_removed,
            "cutoff": self.cutoff.isoformat(),
            "retention_days": self.retention_days,
        }


class RetentionService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._loader = VectorLoader(session)

    async def cleanup_old_articles(self) -> RetentionCleanupResult:
        cutoff = datetime.now(timezone.utc) - timedelta(days=settings.article_retention_days)
        old_articles = list(
            (await self._session.execute(select(Article).where(Article.created_at < cutoff))).scalars().all()
        )

        logger.info(
            "Retention cleanup start retention_days=%s cutoff=%s candidates=%s",
            settings.article_retention_days,
            cutoff.isoformat(),
            len(old_articles),
        )

        vectors_removed = 0
        for article in old_articles:
            await self._loader.delete_article_vectors(article)
            vectors_removed += 1

        result = await self._session.execute(delete(Article).where(Article.created_at < cutoff))
        await self._session.commit()

        deleted_count = int(result.rowcount or 0)
        if deleted_count > 0:
            cache_service.invalidate_search_cache()

        logger.info(
            "Retention cleanup complete deleted=%s vectors_removed=%s",
            deleted_count,
            vectors_removed,
        )
        return RetentionCleanupResult(
            deleted_count=deleted_count,
            vectors_removed=vectors_removed,
            cutoff=cutoff,
            retention_days=settings.article_retention_days,
        )
