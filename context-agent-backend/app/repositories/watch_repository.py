from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.watch import Watch


class WatchRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self, user_id: UUID, keyword: str, entity_id: UUID | None = None
    ) -> Watch:
        watch = Watch(
            user_id=user_id,
            keyword=keyword.strip(),
            entity_id=entity_id,
            is_active=True,
        )
        self._session.add(watch)
        await self._session.commit()
        await self._session.refresh(watch)
        return watch

    async def get_by_id(self, watch_id: UUID, user_id: UUID | None = None) -> Watch | None:
        stmt = select(Watch).where(Watch.id == watch_id)
        if user_id:
            stmt = stmt.where(Watch.user_id == user_id)
        return await self._session.scalar(stmt)

    async def get_by_user_and_keyword(self, user_id: UUID, keyword: str) -> Watch | None:
        stmt = select(Watch).where(
            Watch.user_id == user_id,
            func.lower(Watch.keyword) == func.lower(keyword.strip()),
        )
        return await self._session.scalar(stmt)

    async def list_for_user(self, user_id: UUID) -> list[Watch]:
        stmt = (
            select(Watch)
            .where(Watch.user_id == user_id, Watch.is_active.is_(True))
            .order_by(Watch.created_at.desc())
        )
        return list((await self._session.scalars(stmt)).all())

    async def count_for_user(self, user_id: UUID) -> int:
        stmt = (
            select(func.count())
            .select_from(Watch)
            .where(Watch.user_id == user_id, Watch.is_active.is_(True))
        )
        result = await self._session.scalar(stmt)
        return int(result or 0)

    async def delete(self, watch: Watch) -> None:
        await self._session.delete(watch)
        await self._session.commit()

    async def list_all_active(self) -> list[Watch]:
        stmt = (
            select(Watch)
            .where(Watch.is_active.is_(True))
            .options(selectinload(Watch.user))
            .order_by(Watch.created_at.asc())
        )
        return list((await self._session.scalars(stmt)).all())
