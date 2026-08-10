from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ingestion.hasher import content_hash
from app.models.article import Article
from app.schemas.article import NormalizedArticleDTO


def _merge_categories(existing: list[str], incoming: list[str]) -> list[str]:
    seen: set[str] = set()
    merged: list[str] = []
    for name in existing + incoming:
        key = name.strip().lower()
        if not key or key in seen:
            continue
        seen.add(key)
        merged.append(name.strip())
    return merged


class ArticleRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def upsert(self, article: NormalizedArticleDTO) -> tuple[Article, bool, bool]:
        """Insert article or merge categories on (source, url) conflict.

        Returns (article, created, content_changed).
        """
        now = datetime.now(timezone.utc)
        text_hash = content_hash(article.cleaned_text) if article.cleaned_text else None

        existing = await self._session.scalar(
            select(Article).where(
                Article.source == article.source,
                Article.url == article.url,
            )
        )

        if existing:
            content_changed = text_hash is not None and text_hash != existing.content_hash
            existing.categories = _merge_categories(existing.categories, article.categories)
            if content_changed:
                existing.title = article.title
                existing.summary = article.summary
                existing.image_url = article.image_url
                existing.author = article.author
                existing.published_at = article.published_at
                existing.cleaned_text = article.cleaned_text
                existing.content_hash = text_hash
            existing.updated_at = now
            await self._session.commit()
            await self._session.refresh(existing)
            return existing, False, content_changed

        new_article = Article(
            title=article.title,
            summary=article.summary,
            url=article.url,
            image_url=article.image_url,
            source=article.source,
            author=article.author,
            published_at=article.published_at,
            categories=article.categories,
            cleaned_text=article.cleaned_text,
            content_hash=text_hash,
        )
        self._session.add(new_article)
        await self._session.commit()
        await self._session.refresh(new_article)
        return new_article, True, True

    async def list_articles(
        self,
        *,
        limit: int = 20,
        source: str | None = None,
    ) -> list[Article]:
        query = select(Article).order_by(Article.published_at.desc()).limit(limit)
        if source:
            query = query.where(Article.source == source)
        result = await self._session.execute(query)
        return list(result.scalars().all())

    async def get_by_id(self, article_id) -> Article | None:
        return await self._session.get(Article, article_id)

    async def delete_by_id(self, article_id) -> bool:
        article = await self.get_by_id(article_id)
        if not article:
            return False
        await self._session.delete(article)
        await self._session.commit()
        return True

    async def update_qdrant_point_ids(self, article: Article, point_ids: list) -> Article:
        article.qdrant_point_ids = point_ids
        await self._session.commit()
        await self._session.refresh(article)
        return article
