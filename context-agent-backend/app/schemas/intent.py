from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field


class QueryIntent(StrEnum):
    SINGLE_FACT = "single_fact"
    CONTEXT = "context"
    FOLLOW_UP = "follow_up"


class ChatTurn(BaseModel):
    role: Literal["user", "assistant"]
    text: str = Field(min_length=1, max_length=4000)


class IntentClassification(BaseModel):
    intent: QueryIntent
    confidence: float = Field(ge=0.0, le=1.0)
    reason: str = ""
