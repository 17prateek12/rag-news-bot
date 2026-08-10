from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.agent import ContextSection, RAGResponse, SourceCitation


class ChatSessionCreate(BaseModel):
    title: str | None = Field(default=None, max_length=255)


class ChatSessionRead(BaseModel):
    id: UUID
    title: str
    created_at: datetime


class ChatMessageRead(BaseModel):
    id: UUID
    role: str
    text: str
    sources: list[dict] = Field(default_factory=list)
    created_at: datetime


class ChatSendRequest(BaseModel):
    query: str = Field(min_length=1, max_length=2000)
    limit: int = Field(default=6, ge=1, le=20)


class ChatSendResponse(BaseModel):
    session_id: UUID
    user_message: ChatMessageRead
    assistant_message: ChatMessageRead
    intent: str
    intent_confidence: float
    intent_reason: str
    sections: list[ContextSection] = Field(default_factory=list)
    sources: list[SourceCitation] = Field(default_factory=list)
    input_mode: str = "text"
    transcript: str | None = None

    @classmethod
    def from_rag(
        cls,
        *,
        session_id: UUID,
        user_message: ChatMessageRead,
        assistant_message: ChatMessageRead,
        rag: RAGResponse,
        input_mode: str = "text",
        transcript: str | None = None,
    ) -> "ChatSendResponse":
        return cls(
            session_id=session_id,
            user_message=user_message,
            assistant_message=assistant_message,
            intent=rag.intent,
            intent_confidence=rag.intent_confidence,
            intent_reason=rag.intent_reason,
            sections=rag.sections,
            sources=rag.sources,
            input_mode=input_mode,
            transcript=transcript,
        )
