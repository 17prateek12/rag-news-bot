from pydantic import BaseModel, Field


class TrendingEntityResponse(BaseModel):
    id: str
    canonical_name: str
    entity_type: str | None = None
    rank: int
    score_level: str


class TrendingResponse(BaseModel):
    window: str = "24h"
    trending_news: list[TrendingEntityResponse] = Field(default_factory=list)
    trending_searches: list[TrendingEntityResponse] = Field(default_factory=list)
