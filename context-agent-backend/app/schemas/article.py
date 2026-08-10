from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class NormalizedArticleDTO(BaseModel):
    """Canonical article shape produced by RSS parsers."""

    title: str
    summary: str | None = None
    body: str | None = None
    url: str
    image_url: str | None = None
    source: str
    author: str | None = None
    published_at: datetime
    categories: list[str] = Field(default_factory=list)
    cleaned_text: str | None = None


class ArticleCreate(BaseModel):
    title: str = Field(min_length=1)
    url: str = Field(min_length=1)
    source: str = Field(min_length=1, max_length=100)
    summary: str | None = None
    image_url: str | None = None
    author: str | None = None
    published_at: datetime
    categories: list[str] = Field(default_factory=list)


class ArticleRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    summary: str | None
    url: str
    image_url: str | None
    source: str
    author: str | None
    published_at: datetime
    categories: list[str]
    content_hash: str | None = None
    chunk_count: int = 0
    created_at: datetime
    updated_at: datetime | None
