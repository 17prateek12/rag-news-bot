from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.admin_auth import get_current_admin
from app.core.database import get_db
from app.models.admin import Admin
from app.repositories.category_repository import CategoryRepository
from app.repositories.rss_source_repository import RssSourceRepository
from app.schemas.rss_source import (
    RssSourceCreate,
    RssSourceReadDetailed,
    RssSourceUpdate,
)

router = APIRouter(prefix="/admin/rss-sources", tags=["admin-rss-sources"])


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


@router.post("", response_model=RssSourceReadDetailed, status_code=status.HTTP_201_CREATED)
async def create_rss_source(
    payload: RssSourceCreate,
    _: Admin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    category_repo = CategoryRepository(db)
    rss_repo = RssSourceRepository(db)

    category = await category_repo.get_by_id(payload.category_id)
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")

    existing = await rss_repo.get_by_feed_url(payload.feed_url.strip())
    if existing:
        raise HTTPException(status_code=400, detail="Feed URL already exists")

    try:
        row = await rss_repo.create(
            source=payload.source.strip(),
            category_id=payload.category_id,
            feed_url=payload.feed_url.strip(),
            parser_key=payload.parser_key.strip().lower(),
            is_active=payload.is_active,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    row = await rss_repo.get_by_id(row.id)
    return _to_detailed(row)


@router.patch("/{source_id}", response_model=RssSourceReadDetailed)
async def update_rss_source(
    source_id: int,
    payload: RssSourceUpdate,
    _: Admin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    rss_repo = RssSourceRepository(db)
    category_repo = CategoryRepository(db)

    row = await rss_repo.get_by_id(source_id)
    if not row:
        raise HTTPException(status_code=404, detail="RSS source not found")

    updates = payload.model_dump(exclude_unset=True)
    if "category_id" in updates:
        category = await category_repo.get_by_id(updates["category_id"])
        if not category:
            raise HTTPException(status_code=404, detail="Category not found")
    if "feed_url" in updates:
        updates["feed_url"] = updates["feed_url"].strip()
        existing = await rss_repo.get_by_feed_url(updates["feed_url"])
        if existing and existing.id != source_id:
            raise HTTPException(status_code=400, detail="Feed URL already exists")
    if "source" in updates:
        updates["source"] = updates["source"].strip()
    if "parser_key" in updates:
        updates["parser_key"] = updates["parser_key"].strip().lower()

    try:
        await rss_repo.update(row, **updates)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    row = await rss_repo.get_by_id(source_id)
    return _to_detailed(row)


@router.delete("/{source_id}", status_code=status.HTTP_204_NO_CONTENT)
async def deactivate_rss_source(
    source_id: int,
    _: Admin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    rss_repo = RssSourceRepository(db)
    row = await rss_repo.get_by_id(source_id)
    if not row:
        raise HTTPException(status_code=404, detail="RSS source not found")
    await rss_repo.soft_delete(row)
