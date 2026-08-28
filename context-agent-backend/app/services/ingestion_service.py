import json
import logging
from datetime import datetime, timezone

from app.core.database import AsyncSessionLocal
from app.ingestion.orchestrator import IngestOrchestrator
from app.core.redis_client import get_sync_redis

logger = logging.getLogger(__name__)


async def run_ingestion() -> dict:
    """Shared ingestion entry point.

    Attempts to acquire the global Redis ingestion lock to prevent overlapping runs.
    If the lock is successfully acquired, it instantiates IngestOrchestrator with
    an isolated database session and triggers feed ingestion. It publishes a news:updates
    event if any article was saved or updated, and releases the Redis lock in a finally block.
    """
    redis_client = get_sync_redis()
    lock_key = "lock:ingest:all"
    
    # Check/acquire lock with 2-hour (7200 seconds) expiration
    if not redis_client.set(lock_key, "true", ex=7200, nx=True):
        logger.warning("Ingestion is already running. Skipping execution.")
        return {
            "status": "skipped",
            "reason": "already_running",
            "message": "Another ingestion is already running."
        }

    try:
        logger.info("Ingestion process started")
        async with AsyncSessionLocal() as session:
            orchestrator = IngestOrchestrator(session)
            results = await orchestrator.run_all()
            payload = {
                "status": "completed",
                "feeds_processed": len(results),
                "saved": sum(result.saved for result in results),
                "updated": sum(result.updated for result in results),
                "embedded": sum(result.embedded for result in results),
                "errors": sum(len(result.errors) for result in results),
                "message": "Global feed ingestion has completed."
            }

        logger.info("Ingestion process complete. payload=%s", payload)

        # Publish updates event if new articles saved/embedded
        if payload.get("saved", 0) > 0 or payload.get("embedded", 0) > 0:
            try:
                update_msg = {
                    "event": "news_updated",
                    "saved": payload.get("saved", 0),
                    "embedded": payload.get("embedded", 0),
                    "source": "all",
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
                redis_client.publish("news:updates", json.dumps(update_msg))
                logger.info("Published news:updates event to Redis")
            except Exception as pub_err:
                logger.error("Failed to publish news update to Redis: %s", pub_err)

        return payload
    finally:
        redis_client.delete(lock_key)
