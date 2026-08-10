import asyncio
import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.repositories.article_repository import ArticleRepository
from app.repositories.qdrant_repo import qdrant_repository
from app.schemas.article import ArticleRead

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/articles", tags=["articles"])


@router.get("", response_model=list[ArticleRead])
async def list_articles(
    limit: int = Query(default=20, ge=1, le=100),
    source: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    repo = ArticleRepository(db)
    return await repo.list_articles(limit=limit, source=source)


@router.get("/{article_id}", response_model=ArticleRead)
async def get_article(
    article_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    repo = ArticleRepository(db)
    article = await repo.get_by_id(article_id)
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    return article


@router.get("/{article_id}/chunks")
async def list_article_chunks(
    article_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    repo = ArticleRepository(db)
    article = await repo.get_by_id(article_id)
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    chunks = await asyncio.to_thread(qdrant_repository.list_chunks_for_article, article_id)
    return {
        "article_id": str(article_id),
        "title": article.title,
        "chunk_count": len(chunks),
        "chunks": chunks,
    }
