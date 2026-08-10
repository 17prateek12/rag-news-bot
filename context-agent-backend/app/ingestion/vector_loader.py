import asyncio
import logging
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.exceptions import AppError
from app.ingestion.chunker import chunk_text
from app.models.article import Article
from app.repositories.chunk_repository import ChunkRepository
from app.repositories.embedding_service import embedding_service
from app.repositories.qdrant_repo import qdrant_repository

logger = logging.getLogger(__name__)


@dataclass
class EmbedResult:
    embedded: bool
    skipped: bool
    chunk_count: int = 0
    error: str | None = None
    error_code: str | None = None


class VectorLoader:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def embed_article(self, article: Article, *, force: bool = False) -> EmbedResult:
        logger.info(
            "Embedding article id=%s source=%s force=%s title=%r",
            article.id,
            article.source,
            force,
            article.title[:80],
        )

        if not article.cleaned_text:
            logger.warning("Skipping embed: no cleaned_text article_id=%s", article.id)
            return EmbedResult(
                embedded=False,
                skipped=True,
                error="No cleaned_text to embed",
                error_code="EMBED_NO_CONTENT",
            )

        chunks = chunk_text(
            article.cleaned_text,
            chunk_size=settings.chunk_size,
            overlap=settings.chunk_overlap,
        )
        if not chunks:
            logger.warning("Skipping embed: no chunks article_id=%s", article.id)
            return EmbedResult(
                embedded=False,
                skipped=True,
                error="No chunks produced",
                error_code="EMBED_NO_CHUNKS",
            )

        try:
            logger.debug(
                "Chunked article_id=%s chunks=%s avg_len=%s",
                article.id,
                len(chunks),
                sum(len(chunk) for chunk in chunks) // len(chunks),
            )
            vectors = await asyncio.to_thread(embedding_service.embed_batch, chunks)
            if article.qdrant_point_ids:
                logger.debug(
                    "Removing old vectors article_id=%s count=%s",
                    article.id,
                    len(article.qdrant_point_ids),
                )
                await asyncio.to_thread(qdrant_repository.delete_points, article.qdrant_point_ids)

            point_ids = await asyncio.to_thread(
                qdrant_repository.upsert_chunks,
                article_id=article.id,
                title=article.title,
                source=article.source,
                url=article.url,
                published_at=article.published_at,
                categories=article.categories,
                chunks=chunks,
                vectors=vectors,
            )
            article.qdrant_point_ids = point_ids
            await self._session.commit()
            chunk_repo = ChunkRepository(self._session)
            await chunk_repo.replace_for_article(article, chunks, point_ids)
            await self._session.refresh(article)
            logger.info(
                "Embedded article id=%s chunks=%s qdrant_points=%s",
                article.id,
                len(chunks),
                len(point_ids),
            )
            return EmbedResult(embedded=True, skipped=False, chunk_count=len(point_ids))
        except AppError as exc:
            logger.error(
                "Embed failed article_id=%s code=%s message=%s",
                article.id,
                exc.code,
                exc.message,
            )
            return EmbedResult(
                embedded=False,
                skipped=False,
                error=exc.message,
                error_code=exc.code,
            )
        except Exception as exc:
            logger.exception("Unexpected embed failure article_id=%s", article.id)
            return EmbedResult(
                embedded=False,
                skipped=False,
                error=str(exc),
                error_code="EMBEDDING_FAILED",
            )

    async def delete_article_vectors(self, article: Article) -> None:
        logger.info("Deleting vectors article_id=%s", article.id)
        chunk_repo = ChunkRepository(self._session)
        await chunk_repo.delete_for_article(article.id)
        if article.qdrant_point_ids:
            await asyncio.to_thread(qdrant_repository.delete_points, article.qdrant_point_ids)
        else:
            await asyncio.to_thread(qdrant_repository.delete_by_article_id, article.id)
