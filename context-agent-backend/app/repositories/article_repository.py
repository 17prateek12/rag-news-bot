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
        """Insert article or merge categories on (source_id, url) conflict.

        Returns (article, created, content_changed).
        """
        from app.models.source import Source
        from app.models.category import Category

        now = datetime.now(timezone.utc)
        text_hash = content_hash(article.cleaned_text) if article.cleaned_text else None

        # 1. Resolve source name to ID
        source_row = await self._session.scalar(
            select(Source).where(Source.name == article.source)
        )
        if not source_row:
            source_row = Source(name=article.source)
            self._session.add(source_row)
            await self._session.flush()
        source_id = source_row.id

        # 2. Resolve category names to Category objects
        category_objects: list[Category] = []
        for cat_name in article.categories:
            cat_row = await self._session.scalar(
                select(Category).where(Category.name == cat_name)
            )
            if not cat_row:
                cat_row = Category(name=cat_name)
                self._session.add(cat_row)
                await self._session.flush()
            category_objects.append(cat_row)

        # 3. Query existing article on (source_id, url)
        existing = await self._session.scalar(
            select(Article).where(
                Article.source_id == source_id,
                Article.url == article.url,
            )
        )

        if existing:
            content_changed = text_hash is not None and text_hash != existing.content_hash
            
            # Merge categories
            for cat in category_objects:
                if cat not in existing.categories_relation:
                    existing.categories_relation.append(cat)

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

        # 4. Insert new article
        new_article = Article(
            title=article.title,
            summary=article.summary,
            url=article.url,
            image_url=article.image_url,
            source_id=source_id,
            author=article.author,
            published_at=article.published_at,
            categories_relation=category_objects,
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
        limit: int | None = None,
        source: str | None = None,
        category: str | None = None,
    ) -> list[Article]:
        query = select(Article).order_by(Article.published_at.desc())
        if limit is not None:
            query = query.limit(limit)
        if source:
            from app.models.source import Source
            query = query.join(Article.source_relation).where(Source.name == source)
        if category:
            from app.models.category import Category
            query = query.join(Article.categories_relation).where(Category.name == category)
        result = await self._session.execute(query)
        return list(result.scalars().all())

    async def list_articles_paginated(
        self,
        *,
        page_no: int = 1,
        limit: str | int | None = 20,
        source: str | None = None,
        category: str | None = None,
    ) -> tuple[list[Article], int]:
        from sqlalchemy import func
        count_query = select(func.count(Article.id))
        fetch_query = select(Article).order_by(Article.published_at.desc())

        if source:
            from app.models.source import Source
            count_query = count_query.join(Article.source_relation).where(Source.name == source)
            fetch_query = fetch_query.join(Article.source_relation).where(Source.name == source)
        if category:
            from app.models.category import Category
            count_query = count_query.join(Article.categories_relation).where(Category.name == category)
            fetch_query = fetch_query.join(Article.categories_relation).where(Category.name == category)

        total = await self._session.scalar(count_query) or 0

        limit_val = None
        if limit is not None:
            if str(limit).lower() == "all":
                limit_val = None
            else:
                try:
                    limit_val = int(limit)
                except ValueError:
                    limit_val = 20

        if limit_val is not None:
            offset = (page_no - 1) * limit_val
            fetch_query = fetch_query.limit(limit_val).offset(offset)

        result = await self._session.execute(fetch_query)
        articles = list(result.scalars().all())
        return articles, total

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
