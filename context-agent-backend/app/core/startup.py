import asyncio
import logging
import traceback

from app.config import settings
from app.core.bootstrap import run_bootstrap
from app.core.database import AsyncSessionLocal
from app.core.logging_config import setup_logging
from app.core.migrations import run_migrations
from app.core.security import hash_password
from app.repositories.admin_repository import AdminRepository
from app.repositories.qdrant_repo import qdrant_repository

logger = logging.getLogger(__name__)


async def ensure_singleton_admin() -> None:
    """Create exactly one admin from env on first startup. No public signup endpoint."""
    async with AsyncSessionLocal() as session:
        repo = AdminRepository(session)
        count = await repo.count()
        if count > 0:
            logger.info("Admin already exists count=%s", count)
            return

        if not settings.admin_email or not settings.admin_password:
            logger.warning(
                "No admin in database. Set ADMIN_EMAIL and ADMIN_PASSWORD in .env."
            )
            return

        await repo.create(
            email=settings.admin_email,
            hashed_password=hash_password(settings.admin_password),
        )
        logger.info("Created singleton admin email=%s", settings.admin_email)


async def run_startup() -> None:
    try:
        logger.info("=== Startup begin ===")
        logger.info("Step 1/4: Running database migrations")
        await run_migrations()
        setup_logging()  # Alembic fileConfig resets logging handlers during migrations
        logger.info("Step 2/4: Ensuring singleton admin exists")
        await ensure_singleton_admin()
        logger.info("Step 3/4: Bootstrapping categories and RSS feeds")
        await run_bootstrap()
        logger.info("Step 4/4: Ensuring Qdrant collection exists")
        await asyncio.to_thread(qdrant_repository.ensure_collection)
        if not settings.gcp_project:
            logger.warning(
                "GCP_PROJECT is not set. Ingest will save articles but embeddings will fail."
            )
        logger.info("=== Startup complete ===")
    except Exception:
        logger.exception("Application startup failed")
        traceback.print_exc()
        raise
