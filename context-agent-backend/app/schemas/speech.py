from pydantic import BaseModel, Field


class TranscribeResponse(BaseModel):
    text: str = Field(min_length=1)
    language: str | None = None
    model: str
