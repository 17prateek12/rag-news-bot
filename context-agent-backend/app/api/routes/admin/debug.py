import asyncio
import logging

from fastapi import APIRouter, Depends

from app.core.admin_auth import get_current_admin
from app.models.admin import Admin
from app.repositories.qdrant_repo import qdrant_repository

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin/debug", tags=["admin-debug"])


@router.get("/qdrant/status")
async def qdrant_status(_: Admin = Depends(get_current_admin)):
    """Ops-only: Qdrant health check (admin)."""
    info = await asyncio.to_thread(qdrant_repository.collection_info)
    return info
