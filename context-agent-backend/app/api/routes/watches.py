from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.user_auth import get_current_user
from app.models.user import User
from app.repositories.watch_repository import WatchRepository
from app.schemas.watch import WatchCreate, WatchRead
from app.services.digest_service import resolve_canonical_entity

router = APIRouter(prefix="/watches", tags=["watches"])

MAX_WATCHES_PER_USER = 5


@router.post("", response_model=WatchRead, status_code=status.HTTP_201_CREATED)
async def create_watch(
    payload: WatchCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    repo = WatchRepository(db)

    # 1. Enforce watch limit
    current_count = await repo.count_for_user(current_user.id)
    if current_count >= MAX_WATCHES_PER_USER:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Maximum watch limit ({MAX_WATCHES_PER_USER}) reached. Please remove an existing watch first.",
        )

    # 2. Prevent duplicate watch for the same keyword
    existing = await repo.get_by_user_and_keyword(current_user.id, payload.keyword)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"You are already watching '{payload.keyword}'.",
        )

    # 3. Case-insensitive lookup for matching TrendingEntity
    matched_entity = await resolve_canonical_entity(payload.keyword, db)
    entity_id = matched_entity.id if matched_entity else None

    # 4. Save watch
    watch = await repo.create(
        user_id=current_user.id,
        keyword=payload.keyword,
        entity_id=entity_id,
    )
    return watch


@router.get("", response_model=list[WatchRead])
async def list_watches(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    repo = WatchRepository(db)
    return await repo.list_for_user(current_user.id)


@router.delete("/{watch_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_watch(
    watch_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    repo = WatchRepository(db)
    watch = await repo.get_by_id(watch_id, user_id=current_user.id)
    if not watch:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Watch not found"
        )
    await repo.delete(watch)
