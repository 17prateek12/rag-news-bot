from pydantic import BaseModel, Field


class SearchHit(BaseModel):
    article_id: str
    title: str
    chunk: str
    source: str
    url: str
    publish_date: str | None = None
    categories: list[str] = Field(default_factory=list)
    chunk_index: int | None = None
    semantic_score: float | None = None
    bm25_score: float | None = None
    rrf_score: float | None = None
    rerank_score: float | None = None
    semantic_rank: int | None = None
    bm25_rank: int | None = None


class HybridSearchResponse(BaseModel):
    query: str
    limit: int
    semantic_count: int
    bm25_count: int
    results: list[SearchHit]
