import logging

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.admin_auth import get_current_admin
from app.core.database import get_db
from app.ingestion.orchestrator import IngestOrchestrator
from app.models.admin import Admin

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin/ingest", tags=["admin-ingest"])


@router.post("/run")
async def run_ingest_all(
    _: Admin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    logger.info("Admin ingest all requested")
    orchestrator = IngestOrchestrator(db)
    results = await orchestrator.run_all()
    return {
        "feeds_processed": len(results),
        "results": [result.__dict__ for result in results],
    }


@router.post("/run/{source_id}")
async def run_ingest_one(
    source_id: int,
    _: Admin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    logger.info("Admin ingest requested source_id=%s", source_id)
    orchestrator = IngestOrchestrator(db)
    result = await orchestrator.run_by_id(source_id)
    return result.__dict__
