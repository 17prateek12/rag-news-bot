from celery import Celery
from celery.schedules import crontab

from app.config import settings

celery_app = Celery(
    "context_agent",
    broker=settings.celery_broker_url or settings.redis_url,
    backend=settings.celery_result_backend or settings.redis_url,
    include=["app.worker.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
)

if settings.scheduler_enabled:
    celery_app.conf.beat_schedule = {
        "ingest-all-feeds": {
            "task": "app.worker.tasks.ingest_all_feeds",
            "schedule": crontab(minute=0, hour=f"*/{settings.ingest_interval_hours}"),
        },
        "cleanup-old-articles": {
            "task": "app.worker.tasks.cleanup_old_articles",
            "schedule": crontab(
                hour=settings.retention_cron_hour,
                minute=settings.retention_cron_minute,
            ),
        },
    }
else:
    celery_app.conf.beat_schedule = {}
