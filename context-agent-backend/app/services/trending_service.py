import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

import sqlalchemy as sa
from sqlalchemy import func, select, delete
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.trending import TrendingEntity, TrendingNewsCount, TrendingQueryCount
from app.models.article import Article, article_entities

logger = logging.getLogger(__name__)


def get_current_hour_bucket() -> datetime:
    now = datetime.now(timezone.utc)
    return now.replace(minute=0, second=0, microsecond=0)


class TrendingService:
    async def increment_news_count(self, entity_id: uuid.UUID, db: AsyncSession) -> None:
        bucket = get_current_hour_bucket()
        try:
            stmt = insert(TrendingNewsCount).values(
                entity_id=entity_id,
                hour_bucket=bucket,
                count=1
            ).on_conflict_do_update(
                index_elements=['entity_id', 'hour_bucket'],
                set_=dict(count=TrendingNewsCount.count + 1)
            )
            await db.execute(stmt)
            await db.commit()
        except Exception as exc:
            logger.error("Failed to increment news count for entity %s: %s", entity_id, exc)

    async def increment_query_count(self, entity_id: uuid.UUID, db: AsyncSession) -> None:
        bucket = get_current_hour_bucket()
        try:
            stmt = insert(TrendingQueryCount).values(
                entity_id=entity_id,
                hour_bucket=bucket,
                count=1
            ).on_conflict_do_update(
                index_elements=['entity_id', 'hour_bucket'],
                set_=dict(count=TrendingQueryCount.count + 1)
            )
            await db.execute(stmt)
            await db.commit()
        except Exception as exc:
            logger.error("Failed to increment query count for entity %s: %s", entity_id, exc)

    def _map_heat_level(self, score: int, max_score: int) -> str:
        if max_score <= 0:
            return "active"
        ratio = score / max_score
        if ratio >= 0.7:
            return "hot"
        elif ratio >= 0.3:
            return "warm"
        return "active"

    async def get_trending_news(self, db: AsyncSession, limit: int = 10) -> list[dict[str, Any]]:
        since = datetime.now(timezone.utc) - timedelta(hours=24)
        since = since.replace(minute=0, second=0, microsecond=0)

        # Select sum of count grouped by entity
        stmt = (
            select(
                TrendingEntity.id,
                TrendingEntity.canonical_name,
                TrendingEntity.entity_type,
                func.sum(TrendingNewsCount.count).label("score")
            )
            .join(TrendingNewsCount, TrendingNewsCount.entity_id == TrendingEntity.id)
            .filter(TrendingNewsCount.hour_bucket >= since)
            .group_by(TrendingEntity.id, TrendingEntity.canonical_name, TrendingEntity.entity_type)
            .order_by(sa.desc("score"))
            .limit(limit)
        )

        result = await db.execute(stmt)
        rows = result.all()
        if not rows:
            return []

        max_score = int(rows[0][3] or 0)
        items = []
        for idx, row in enumerate(rows):
            entity_id, canonical_name, entity_type, score = row
            score_val = int(score or 0)
            items.append({
                "id": str(entity_id),
                "canonical_name": canonical_name,
                "entity_type": entity_type,
                "rank": idx + 1,
                "score_level": self._map_heat_level(score_val, max_score)
            })
        return items

    async def get_trending_searches(self, db: AsyncSession, limit: int = 10) -> list[dict[str, Any]]:
        since = datetime.now(timezone.utc) - timedelta(hours=24)
        since = since.replace(minute=0, second=0, microsecond=0)

        stmt = (
            select(
                TrendingEntity.id,
                TrendingEntity.canonical_name,
                TrendingEntity.entity_type,
                func.sum(TrendingQueryCount.count).label("score")
            )
            .join(TrendingQueryCount, TrendingQueryCount.entity_id == TrendingEntity.id)
            .filter(TrendingQueryCount.hour_bucket >= since)
            .group_by(TrendingEntity.id, TrendingEntity.canonical_name, TrendingEntity.entity_type)
            .order_by(sa.desc("score"))
            .limit(limit)
        )

        result = await db.execute(stmt)
        rows = result.all()
        if not rows:
            return []

        max_score = int(rows[0][3] or 0)
        items = []
        for idx, row in enumerate(rows):
            entity_id, canonical_name, entity_type, score = row
            score_val = int(score or 0)
            items.append({
                "id": str(entity_id),
                "canonical_name": canonical_name,
                "entity_type": entity_type,
                "rank": idx + 1,
                "score_level": self._map_heat_level(score_val, max_score)
            })
        return items

    async def clean_old_counts(self, db: AsyncSession) -> None:
        thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)
        
        # 1. Delete news count buckets older than 30 days
        stmt1 = delete(TrendingNewsCount).where(TrendingNewsCount.hour_bucket < thirty_days_ago)
        await db.execute(stmt1)

        # 2. Delete query count buckets older than 30 days
        stmt2 = delete(TrendingQueryCount).where(TrendingQueryCount.hour_bucket < thirty_days_ago)
        await db.execute(stmt2)
        
        await db.commit()
        logger.info("Successfully cleaned up old trending hourly count buckets older than 30 days")


trending_service = TrendingService()
