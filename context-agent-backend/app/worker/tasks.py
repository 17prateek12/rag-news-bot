import asyncio
from datetime import datetime, timezone
import json
import logging

from app.core.database import AsyncSessionLocal
from app.core.logging_config import setup_logging
from app.ingestion.orchestrator import IngestOrchestrator
from app.services.ingestion_service import run_ingestion
from app.services.retention_service import RetentionService
from app.worker.celery_app import celery_app

from app.core.redis_client import get_sync_redis

logger = logging.getLogger(__name__)


def _run_async(coro):
    return asyncio.run(coro)


@celery_app.task(name="app.worker.tasks.ingest_all_feeds")
def ingest_all_feeds() -> dict:
    setup_logging()
    logger.info("Scheduled ingest task started (Celery)")
    payload = _run_async(run_ingestion())
    logger.info("Scheduled ingest task complete payload=%s", payload)
    return payload


@celery_app.task(name="app.worker.tasks.ingest_one_feed")
def ingest_one_feed(source_id: int) -> dict:
    setup_logging()

    redis_client = get_sync_redis()
    global_lock = "lock:ingest:all"
    source_lock = f"lock:ingest:source:{source_id}"

    if redis_client.get(global_lock):
        logger.warning("Global ingestion is running. Skipping source ingest for source_id=%s.", source_id)
        return {"status": "skipped", "reason": "Global ingestion in progress"}

    if not redis_client.set(source_lock, "true", ex=600, nx=True):
        logger.warning("Source ingestion for %s is already running. Skipping.", source_id)
        return {"status": "skipped", "reason": "Already running"}

    try:
        async def _run() -> dict:
            async with AsyncSessionLocal() as session:
                orchestrator = IngestOrchestrator(session)
                result = await orchestrator.run_by_id(source_id)
                return result.__dict__

        logger.info("Manual source ingest task started source_id=%s", source_id)
        payload = _run_async(_run())
        logger.info("Manual source ingest task complete payload=%s", payload)

        # Publish updates event if new articles saved/embedded
        if payload.get("saved", 0) > 0 or payload.get("embedded", 0) > 0:
            try:
                update_msg = {
                    "event": "news_updated",
                    "saved": payload.get("saved", 0),
                    "embedded": payload.get("embedded", 0),
                    "source": source_id,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
                redis_client.publish("news:updates", json.dumps(update_msg))
                logger.info("Published news:updates event to Redis for source_id=%s", source_id)
            except Exception as pub_err:
                logger.error("Failed to publish news update to Redis: %s", pub_err)

        return payload
    finally:
        redis_client.delete(source_lock)


@celery_app.task(name="app.worker.tasks.cleanup_old_articles")
def cleanup_old_articles() -> dict:
    setup_logging()

    async def _run() -> dict:
        async with AsyncSessionLocal() as session:
            result = await RetentionService(session).cleanup_old_articles()
            return result.to_dict()

    logger.info("Scheduled retention cleanup task started")
    payload = _run_async(_run())
    logger.info("Scheduled retention cleanup task complete payload=%s", payload)
    return payload


@celery_app.task(name="app.worker.tasks.track_query_trending")
def track_query_trending(query: str) -> dict:
    setup_logging()

    async def _run() -> dict:
        from app.services.entity_service import entity_service
        from app.services.trending_service import trending_service
        async with AsyncSessionLocal() as session:
            entities = await entity_service.extract_entities(query)
            count = 0
            for entity_info in entities:
                entity_obj = await entity_service.get_or_create_canonical_entity(
                    entity_info["name"], entity_info["type"], session
                )
                await trending_service.increment_query_count(entity_obj.id, session)
                count += 1
            return {"query": query, "entities_processed": count}

    logger.info("Background query trending tracking started query=%r", query)
    payload = _run_async(_run())
    logger.info("Background query trending tracking complete payload=%s", payload)
    return payload
