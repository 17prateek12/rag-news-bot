from pydantic import BaseModel, Field


class TrendingQuery(BaseModel):
    topic: str
    query: str
    count: int


class TrendingResponse(BaseModel):
    window: str = "24h"
    queries: list[TrendingQuery] = Field(default_factory=list)
