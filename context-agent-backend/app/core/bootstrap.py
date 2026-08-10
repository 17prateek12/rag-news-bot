from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.bootstrap_data import CATEGORIES, RSS_FEEDS
from app.core.database import AsyncSessionLocal
from app.models.category import Category
from app.models.rss_source import RssSource


async def bootstrap_database(session: AsyncSession | None = None) -> None:
    """Idempotent: add any missing categories and RSS feeds from bootstrap_data."""
    owns_session = session is None
    if owns_session:
        session = AsyncSessionLocal()

    assert session is not None

    try:
        category_map: dict[str, Category] = {}

        for name in CATEGORIES:
            existing = await session.scalar(select(Category).where(Category.name == name))
            if existing:
                category_map[name] = existing
            else:
                category = Category(name=name)
                session.add(category)
                category_map[name] = category

        await session.flush()

        for feed in RSS_FEEDS:
            existing = await session.scalar(
                select(RssSource).where(RssSource.feed_url == feed["feed_url"])
            )
            if existing:
                continue

            session.add(
                RssSource(
                    source=feed["source"],
                    category_id=category_map[feed["category"]].id,
                    feed_url=feed["feed_url"],
                    parser_key=feed["parser_key"],
                    is_active=True,
                )
            )

        await session.commit()
    finally:
        if owns_session:
            await session.close()


async def run_bootstrap() -> None:
    await bootstrap_database()
