from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class WatchCreate(BaseModel):
    keyword: str = Field(min_length=2, max_length=100)

    @field_validator("keyword")
    @classmethod
    def clean_keyword(cls, v: str) -> str:
        cleaned = v.strip()
        if len(cleaned) < 2:
            raise ValueError("Keyword must be at least 2 characters long")
        return cleaned


class WatchRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    keyword: str
    entity_id: UUID | None = None
    is_active: bool
    created_at: datetime


class DigestArticleRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    url: str
    source: str | None = None
    published_at: datetime | None = None


class DigestRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    watch_id: UUID
    keyword: str
    digest_date: date
    summary_text: str
    overview: str = ""
    bullets: list[str] = []
    article_ids: list[UUID]
    articles: list[DigestArticleRead] = []
    created_at: datetime


class DigestRunResponse(BaseModel):
    status: str
    digest_date: str
    unique_keywords_checked: int
    digests_created: int
    digests_skipped: int
    message: str
