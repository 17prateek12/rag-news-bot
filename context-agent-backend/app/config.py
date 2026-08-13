from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Postgres
    postgres_user: str
    postgres_password: str
    postgres_db: str
    postgres_port: int
    postgres_host: str
    database_url: str

    # Redis / Qdrant
    redis_url: str
    cache_enabled: bool
    cache_search_ttl_seconds: int
    cache_rag_ttl_seconds: int
    cache_session_ttl_seconds: int
    cache_trending_enabled: bool
    cache_trending_ttl_seconds: int
    qdrant_url: str
    qdrant_api_key: str
    qdrant_collection: str

    # Vertex AI / Embeddings
    gcp_project: str
    gcp_location: str
    embedding_model: str
    embedding_dimensions: int
    chunk_size: int
    chunk_overlap: int

    # Hybrid search
    hybrid_semantic_limit: int
    hybrid_bm25_limit: int
    hybrid_result_limit: int
    rrf_k: int
    context_chunk_limit: int
    background_search_limit: int
    semantic_similarity_threshold: float
    bm25_relevance_threshold: float

    # Reranker (cross-encoder between retrieval and generation)
    reranker_enabled: bool
    reranker_model: str
    rerank_candidate_limit: int
    relevance_score_floor: float

    # LLM (Vertex AI generation)
    gemini_model: str
    llm_max_output_tokens: int

    # Speech-to-text (Vertex AI / Gemini)
    stt_enabled: bool
    stt_model: str = ""
    stt_max_audio_bytes: int
    stt_max_output_tokens: int

    # Ingest
    article_retention_days: int
    ingest_interval_hours: int

    # Web fallback (Tavily)
    tavily_api_key: str = ""
    web_fallback_enabled: bool
    web_fallback_stale_hours: int
    web_fallback_min_hits: int
    web_fallback_max_results: int
    web_fallback_search_depth: str
    web_fallback_min_semantic_score: float
    web_fallback_cache_ttl_seconds: int

    # Ingest / retention scheduler (Celery)
    celery_broker_url: str = ""
    celery_result_backend: str = ""
    scheduler_enabled: bool
    retention_cron_hour: int
    retention_cron_minute: int

    # API
    api_host: str
    api_port: int
    log_level: str

    # Admin auth
    admin_email: str
    admin_password: str
    admin_api_key: str
    jwt_secret: str
    jwt_algorithm: str
    jwt_expire_minutes: int

    @model_validator(mode="after")
    def adjust_redis_url(self) -> 'Settings':
        for attr in ["redis_url", "celery_broker_url", "celery_result_backend"]:
            val = getattr(self, attr, "")
            if val and val.startswith("rediss://") and "ssl_cert_reqs" not in val:
                separator = "&" if "?" in val else "?"
                setattr(self, attr, f"{val}{separator}ssl_cert_reqs=CERT_NONE")
        return self


settings = Settings()
