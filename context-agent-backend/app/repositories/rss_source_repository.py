from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.bootstrap_data import VALID_PARSER_KEYS
from app.models.rss_source import RssSource


class RssSourceRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_all(self, active_only: bool = False) -> list[RssSource]:
        query = select(RssSource).options(
            selectinload(RssSource.category),
            selectinload(RssSource.source_relation)
        ).order_by(RssSource.id)
        if active_only:
            query = query.where(RssSource.is_active.is_(True))
        result = await self._session.execute(query)
        return list(result.scalars().all())

    async def list_active(self) -> list[RssSource]:
        return await self.list_all(active_only=True)

    async def get_by_id(self, source_id: int) -> RssSource | None:
        result = await self._session.execute(
            select(RssSource)
            .options(
                selectinload(RssSource.category),
                selectinload(RssSource.source_relation)
            )
            .where(RssSource.id == source_id)
        )
        return result.scalar_one_or_none()

    async def get_by_feed_url(self, feed_url: str) -> RssSource | None:
        return await self._session.scalar(
            select(RssSource)
            .options(selectinload(RssSource.category), selectinload(RssSource.source_relation))
            .where(RssSource.feed_url == feed_url)
        )

    async def create(
        self,
        *,
        source_id: int,
        category_id: int,
        feed_url: str,
        parse_key: str,
        is_active: bool = True,
    ) -> RssSource:
        if parse_key not in VALID_PARSER_KEYS:
            raise ValueError(f"Invalid parse_key. Must be one of: {sorted(VALID_PARSER_KEYS)}")
        row = RssSource(
            source_id=source_id,
            category_id=category_id,
            feed_url=feed_url,
            parse_key=parse_key,
            is_active=is_active,
        )
        self._session.add(row)
        await self._session.commit()
        await self._session.refresh(row)
        return row

    async def update(self, row: RssSource, **fields) -> RssSource:
        if "parse_key" in fields and fields["parse_key"] not in VALID_PARSER_KEYS:
            raise ValueError(f"Invalid parse_key. Must be one of: {sorted(VALID_PARSER_KEYS)}")
        for key, value in fields.items():
            if value is not None:
                setattr(row, key, value)
        await self._session.commit()
        await self._session.refresh(row)
        return row

    async def soft_delete(self, row: RssSource) -> RssSource:
        row.is_active = False
        await self._session.commit()
        await self._session.refresh(row)
        return row
