import logging

from fastapi import APIRouter, Depends

from app.core.admin_auth import get_current_admin
from app.models.admin import Admin
from app.schemas.watch import DigestRunResponse
from app.services.digest_service import DigestService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin/digests", tags=["admin-digests"])


@router.post("/run", response_model=DigestRunResponse)
async def run_daily_digests(
    _: Admin = Depends(get_current_admin),
):
    logger.info("Admin triggered daily digest generation run")
    result = await DigestService.run_daily_digests()
    return DigestRunResponse(**result)
