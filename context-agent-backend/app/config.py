from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Postgres
    postgres_user: str = "context_agent"
    postgres_password: str = "changeme"
    postgres_db: str = "context_agent"
    postgres_port: int = 5437
    postgres_host: str = "localhost"
    database_url: str

    # Redis / Qdrant
    redis_url: str = "redis://localhost:6384/0"
    cache_enabled: bool = True
    cache_search_ttl_seconds: int = 1800
    cache_rag_ttl_seconds: int = 900
    cache_session_ttl_seconds: int = 3600
    cache_trending_enabled: bool = True
    cache_trending_ttl_seconds: int = 86400
    qdrant_url: str = "http://localhost:6333"
    qdrant_collection: str = "news_chunks"

    # Vertex AI / Embeddings
    gcp_project: str = ""
    gcp_location: str = "global"
    embedding_model: str = "text-embedding-004"
    embedding_dimensions: int = 768
    chunk_size: int = 800
    chunk_overlap: int = 100

    # Hybrid search
    hybrid_semantic_limit: int = 20
    hybrid_bm25_limit: int = 20
    hybrid_result_limit: int = 6
    rrf_k: int = 60
    context_chunk_limit: int = 8
    background_search_limit: int = 4

    # Reranker (cross-encoder between retrieval and generation)
    reranker_enabled: bool = True
    reranker_model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"
    rerank_candidate_limit: int = 20

    # LLM (Vertex AI generation)
    gemini_model: str = "gemini-2.5-flash"
    llm_max_output_tokens: int = 1024

    # Speech-to-text (Vertex AI / Gemini)
    stt_enabled: bool = True
    stt_model: str = ""
    stt_max_audio_bytes: int = 10 * 1024 * 1024
    stt_max_output_tokens: int = 1024

    # Ingest
    article_retention_days: int = 30
    ingest_interval_hours: int = 6

    # Web fallback (Tavily)
    tavily_api_key: str = ""
    web_fallback_enabled: bool = True
    web_fallback_stale_hours: int = 48
    web_fallback_min_hits: int = 2
    web_fallback_max_results: int = 5
    web_fallback_search_depth: str = "basic"
    web_fallback_min_semantic_score: float = 0.32
    web_fallback_cache_ttl_seconds: int = 900

    # Ingest / retention scheduler (Celery)
    celery_broker_url: str = ""
    celery_result_backend: str = ""
    scheduler_enabled: bool = True
    retention_cron_hour: int = 3
    retention_cron_minute: int = 0

    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    log_level: str = "INFO"

    # Admin auth
    admin_email: str = ""
    admin_password: str = ""
    admin_api_key: str = ""
    jwt_secret: str = "change-me-jwt-secret"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 1440


settings = Settings()
