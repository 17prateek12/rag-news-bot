from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.category import Category
from app.models.rss_source import RssSource


class CategoryRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_all(self) -> list[Category]:
        result = await self._session.execute(select(Category).order_by(Category.name))
        return list(result.scalars().all())

    async def get_by_id(self, category_id: int) -> Category | None:
        return await self._session.get(Category, category_id)

    async def get_by_name(self, name: str) -> Category | None:
        return await self._session.scalar(select(Category).where(Category.name == name))

    async def create(self, name: str) -> Category:
        category = Category(name=name)
        self._session.add(category)
        await self._session.commit()
        await self._session.refresh(category)
        return category

    async def update(self, category: Category, name: str) -> Category:
        category.name = name
        await self._session.commit()
        await self._session.refresh(category)
        return category

    async def delete(self, category: Category) -> None:
        await self._session.delete(category)
        await self._session.commit()

    async def count_active_feeds(self, category_id: int) -> int:
        result = await self._session.scalar(
            select(func.count())
            .select_from(RssSource)
            .where(RssSource.category_id == category_id, RssSource.is_active.is_(True))
        )
        return int(result or 0)
