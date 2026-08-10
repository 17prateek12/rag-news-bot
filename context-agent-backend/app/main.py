from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.admin.articles import router as admin_articles_router
from app.api.routes.admin.auth import router as admin_auth_router
from app.api.routes.admin.categories import router as admin_categories_router
from app.api.routes.admin.debug import router as admin_debug_router
from app.api.routes.admin.ingest import router as admin_ingest_router
from app.api.routes.admin.maintenance import router as admin_maintenance_router
from app.api.routes.admin.rss_sources import router as admin_rss_sources_router
from app.api.routes.agent import router as agent_router
from app.api.routes.auth import router as auth_router
from app.api.routes.chat import router as chat_router
from app.api.routes.articles import router as articles_router
from app.api.routes.categories import router as categories_router
from app.api.routes.health import router as health_router
from app.api.routes.rss_sources import router as rss_sources_router
from app.api.routes.search import router as search_router
from app.api.routes.speech import router as speech_router
from app.api.routes.trending import router as trending_router
from app.core.exception_handlers import register_exception_handlers
from app.core.logging_config import setup_logging
from app.core.request_logging import RequestLoggingMiddleware
from app.core.startup import run_startup

setup_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    await run_startup()
    yield


app = FastAPI(
    title="Context Agent Backend",
    description="Normalized news ingestion and context agent API",
    version="1.0.0",
    lifespan=lifespan,
)

register_exception_handlers(app)

app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Public (no auth)
app.include_router(health_router)
app.include_router(articles_router)
app.include_router(categories_router)
app.include_router(rss_sources_router)
app.include_router(search_router)
app.include_router(trending_router)
app.include_router(agent_router)
app.include_router(auth_router)
app.include_router(speech_router)
app.include_router(chat_router)

# Admin-only (writes + ingest + ops)
app.include_router(admin_auth_router)
app.include_router(admin_articles_router)
app.include_router(admin_categories_router)
app.include_router(admin_rss_sources_router)
app.include_router(admin_ingest_router)
app.include_router(admin_maintenance_router)
app.include_router(admin_debug_router)
