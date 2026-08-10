import uuid
from datetime import datetime

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.article import Article
from app.models.article_chunk import ArticleChunk


class ChunkRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def replace_for_article(
        self,
        article: Article,
        chunks: list[str],
        point_ids: list[uuid.UUID],
    ) -> None:
        await self._session.execute(
            delete(ArticleChunk).where(ArticleChunk.article_id == article.id)
        )
        for idx, chunk_text in enumerate(chunks):
            point_id = point_ids[idx] if idx < len(point_ids) else None
            self._session.add(
                ArticleChunk(
                    article_id=article.id,
                    chunk_index=idx,
                    chunk_text=chunk_text,
                    title=article.title,
                    source=article.source,
                    url=article.url,
                    published_at=article.published_at,
                    categories=article.categories,
                    qdrant_point_id=point_id,
                )
            )
        await self._session.commit()

    async def delete_for_article(self, article_id: uuid.UUID) -> None:
        await self._session.execute(
            delete(ArticleChunk).where(ArticleChunk.article_id == article_id)
        )
        await self._session.commit()

    async def search_bm25(self, query: str, limit: int = 20) -> list[dict]:
        ts_query = func.plainto_tsquery("english", query)
        rank = func.ts_rank_cd(ArticleChunk.search_vector, ts_query).label("bm25_score")

        stmt = (
            select(
                ArticleChunk.article_id,
                ArticleChunk.chunk_index,
                ArticleChunk.chunk_text,
                ArticleChunk.title,
                ArticleChunk.source,
                ArticleChunk.url,
                ArticleChunk.published_at,
                ArticleChunk.categories,
                ArticleChunk.qdrant_point_id,
                rank,
            )
            .where(ArticleChunk.search_vector.op("@@")(ts_query))
            .order_by(rank.desc())
            .limit(limit)
        )
        rows = (await self._session.execute(stmt)).all()
        return [
            {
                "article_id": str(row.article_id),
                "chunk_index": row.chunk_index,
                "chunk": row.chunk_text,
                "title": row.title,
                "source": row.source,
                "url": row.url,
                "publish_date": row.published_at.isoformat(),
                "categories": row.categories,
                "qdrant_point_id": str(row.qdrant_point_id) if row.qdrant_point_id else None,
                "bm25_score": float(row.bm25_score),
            }
            for row in rows
        ]

    async def count_all(self) -> int:
        result = await self._session.scalar(select(func.count()).select_from(ArticleChunk))
        return int(result or 0)
