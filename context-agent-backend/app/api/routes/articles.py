import asyncio
import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.repositories.article_repository import ArticleRepository
from app.repositories.qdrant_repo import qdrant_repository
from app.schemas.article import ArticleRead, ArticleListResponse, ArticleMetadata

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/articles", tags=["articles"])


@router.get("", response_model=ArticleListResponse)
async def list_articles(
    pageNo: int = Query(default=1, ge=1),
    limit: str = Query(default="20"),
    source: str | None = None,
    category: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    repo = ArticleRepository(db)
    articles, total = await repo.list_articles_paginated(
        page_no=pageNo,
        limit=limit,
        source=source,
        category=category,
    )

    try:
        limit_rep = int(limit)
    except ValueError:
        limit_rep = "all"

    return ArticleListResponse(
        metadata=ArticleMetadata(
            pageNo=pageNo,
            limit=limit_rep,
            total=total,
        ),
        articles=[ArticleRead.model_validate(art) for art in articles],
    )


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
