from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.admin_auth import get_current_admin
from app.core.database import get_db
from app.models.admin import Admin
from app.repositories.category_repository import CategoryRepository
from app.schemas.category import CategoryCreate, CategoryRead, CategoryUpdate

router = APIRouter(prefix="/admin/categories", tags=["admin-categories"])


@router.post("", response_model=CategoryRead, status_code=status.HTTP_201_CREATED)
async def create_category(
    payload: CategoryCreate,
    _: Admin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    repo = CategoryRepository(db)
    existing = await repo.get_by_name(payload.name.strip())
    if existing:
        raise HTTPException(status_code=400, detail="Category already exists")
    return await repo.create(payload.name.strip())


@router.patch("/{category_id}", response_model=CategoryRead)
async def update_category(
    category_id: int,
    payload: CategoryUpdate,
    _: Admin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    repo = CategoryRepository(db)
    category = await repo.get_by_id(category_id)
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    name = payload.name.strip()
    existing = await repo.get_by_name(name)
    if existing and existing.id != category_id:
        raise HTTPException(status_code=400, detail="Category name already in use")
    return await repo.update(category, name)


@router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_category(
    category_id: int,
    _: Admin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    repo = CategoryRepository(db)
    category = await repo.get_by_id(category_id)
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    feed_count = await repo.count_active_feeds(category_id)
    if feed_count > 0:
        raise HTTPException(
            status_code=409,
            detail=f"Cannot delete category linked to {feed_count} active RSS feed(s)",
        )
    await repo.delete(category)
