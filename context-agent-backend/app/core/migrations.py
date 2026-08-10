import asyncio
from pathlib import Path

from alembic import command
from alembic.config import Config

from app.config import settings
from app.core.logging_config import setup_logging


def _run_alembic_upgrade() -> None:
    root = Path(__file__).resolve().parents[2]
    cfg = Config(str(root / "alembic.ini"))
    cfg.set_main_option("sqlalchemy.url", settings.database_url)
    command.upgrade(cfg, "head")
    setup_logging()


async def run_migrations() -> None:
    """Apply pending SQL migrations. Existing tables are left unchanged."""
    await asyncio.to_thread(_run_alembic_upgrade)
