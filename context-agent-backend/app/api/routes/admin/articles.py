from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.admin_auth import get_current_admin
from app.core.database import get_db
from app.core.exceptions import EmbeddingError, NotFoundError
from app.ingestion.content_builder import build_cleaned_text
from app.ingestion.vector_loader import VectorLoader
from app.models.admin import Admin
from app.repositories.article_repository import ArticleRepository
from app.schemas.article import ArticleCreate, ArticleRead, NormalizedArticleDTO

router = APIRouter(prefix="/admin/articles", tags=["admin-articles"])


@router.post("", response_model=ArticleRead, status_code=status.HTTP_201_CREATED)
async def create_article(
    payload: ArticleCreate,
    _: Admin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    repo = ArticleRepository(db)
    dto = NormalizedArticleDTO(
        title=payload.title.strip(),
        summary=payload.summary,
        url=payload.url.strip(),
        image_url=payload.image_url,
        source=payload.source.strip(),
        author=payload.author,
        published_at=payload.published_at,
        categories=payload.categories,
    )
    dto.cleaned_text = build_cleaned_text(dto)
    article, _, _ = await repo.upsert(dto)
    return article


@router.post("/{article_id}/reindex")
async def reindex_article(
    article_id: UUID,
    _: Admin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    repo = ArticleRepository(db)
    article = await repo.get_by_id(article_id)
    if not article:
        raise NotFoundError("Article not found", details={"article_id": str(article_id)})
    loader = VectorLoader(db)
    result = await loader.embed_article(article, force=True)
    if result.error and not result.embedded:
        raise EmbeddingError(
            result.error,
            details={
                "article_id": str(article_id),
                "error_code": result.error_code,
            },
        )
    return {
        "article_id": str(article_id),
        "embedded": result.embedded,
        "chunk_count": result.chunk_count,
    }


@router.delete("/{article_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_article(
    article_id: UUID,
    _: Admin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    repo = ArticleRepository(db)
    article = await repo.get_by_id(article_id)
    if not article:
        raise NotFoundError("Article not found", details={"article_id": str(article_id)})
    loader = VectorLoader(db)
    await loader.delete_article_vectors(article)
    await repo.delete_by_id(article_id)
