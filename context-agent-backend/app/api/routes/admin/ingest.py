import logging

from fastapi import APIRouter, Depends

from app.core.admin_auth import get_current_admin
from app.models.admin import Admin
from app.services.ingestion_service import run_ingestion

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin/ingest", tags=["admin-ingest"])


@router.post("/run")
async def run_ingest_all(
    _: Admin = Depends(get_current_admin),
):
    logger.info("Admin ingest all requested - running synchronously")
    return await run_ingestion()


@router.post("/run/{source_id}")
async def run_ingest_one(
    source_id: int,
    _: Admin = Depends(get_current_admin),
):
    logger.info("Admin ingest requested source_id=%s - dispatching to Celery background task", source_id)
    from app.worker.tasks import ingest_one_feed
    task = ingest_one_feed.delay(source_id)
    return {
        "status": "queued",
        "task_id": task.id,
        "message": f"Feed ingestion for source {source_id} has been queued in the background worker."
    }
