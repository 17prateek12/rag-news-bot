from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.repositories.rss_source_repository import RssSourceRepository
from app.schemas.rss_source import RssSourceReadDetailed

router = APIRouter(prefix="/rss-sources", tags=["rss-sources"])


def _to_detailed(row) -> RssSourceReadDetailed:
    return RssSourceReadDetailed(
        id=row.id,
        source=row.source,
        category_id=row.category_id,
        feed_url=row.feed_url,
        parser_key=row.parser_key,
        is_active=row.is_active,
        category_name=row.category.name if row.category else None,
    )


@router.get("", response_model=list[RssSourceReadDetailed])
async def list_rss_sources(db: AsyncSession = Depends(get_db)):
    repo = RssSourceRepository(db)
    rows = await repo.list_all()
    return [_to_detailed(row) for row in rows]
