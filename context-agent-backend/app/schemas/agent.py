from pydantic import BaseModel, Field

from app.schemas.intent import ChatTurn, IntentClassification, QueryIntent


class RAGQueryRequest(BaseModel):
    query: str = Field(min_length=1, max_length=2000)
    limit: int = Field(default=6, ge=1, le=20)
    history: list[ChatTurn] = Field(default_factory=list)


class SourceCitation(BaseModel):
    index: int
    title: str
    source: str
    url: str
    publish_date: str | None = None
    excerpt: str


class ContextSection(BaseModel):
    key: str
    title: str
    content: str


class RAGResponse(BaseModel):
    query: str
    intent: QueryIntent
    intent_confidence: float
    intent_reason: str
    answer: str
    sections: list[ContextSection] = Field(default_factory=list)
    sources: list[SourceCitation]
    retrieval: dict


class ClassifyQueryResponse(BaseModel):
    query: str
    classification: IntentClassification
