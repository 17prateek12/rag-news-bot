import asyncio
import logging

from app.core.database import AsyncSessionLocal
from app.core.logging_config import setup_logging
from app.ingestion.orchestrator import IngestOrchestrator
from app.services.retention_service import RetentionService
from app.worker.celery_app import celery_app

logger = logging.getLogger(__name__)


def _run_async(coro):
    return asyncio.run(coro)


@celery_app.task(name="app.worker.tasks.ingest_all_feeds")
def ingest_all_feeds() -> dict:
    setup_logging()

    async def _run() -> dict:
        async with AsyncSessionLocal() as session:
            orchestrator = IngestOrchestrator(session)
            results = await orchestrator.run_all()
            return {
                "feeds_processed": len(results),
                "saved": sum(result.saved for result in results),
                "updated": sum(result.updated for result in results),
                "embedded": sum(result.embedded for result in results),
                "errors": sum(len(result.errors) for result in results),
            }

    logger.info("Scheduled ingest task started")
    payload = _run_async(_run())
    logger.info("Scheduled ingest task complete payload=%s", payload)
    return payload


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
