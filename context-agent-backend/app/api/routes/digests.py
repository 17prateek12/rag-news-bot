from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.user_auth import get_current_user
from app.models.user import User
from app.repositories.digest_repository import DigestRepository
from app.schemas.watch import DigestRead

router = APIRouter(prefix="/digests", tags=["digests"])


@router.get("", response_model=list[DigestRead])
async def list_digests(
    days: int = Query(default=7, ge=1, le=30),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    repo = DigestRepository(db)
    return await repo.list_recent_for_user(current_user.id, days=days)
