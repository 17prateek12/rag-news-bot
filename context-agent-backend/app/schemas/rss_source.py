from pydantic import BaseModel, ConfigDict, Field


class RssSourceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    source: str
    category_id: int
    feed_url: str
    parser_key: str
    is_active: bool


class RssSourceReadDetailed(RssSourceRead):
    category_name: str | None = None


class RssSourceCreate(BaseModel):
    source: str = Field(min_length=1, max_length=100)
    category_id: int
    feed_url: str = Field(min_length=1)
    parser_key: str = Field(min_length=1, max_length=50)
    is_active: bool = True


class RssSourceUpdate(BaseModel):
    source: str | None = Field(default=None, min_length=1, max_length=100)
    category_id: int | None = None
    feed_url: str | None = Field(default=None, min_length=1)
    parser_key: str | None = Field(default=None, min_length=1, max_length=50)
    is_active: bool | None = None
