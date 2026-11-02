from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from ..models import PostStatus, SourceType


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class SourceCreate(BaseModel):
    type: SourceType
    name: str = Field(min_length=2, max_length=200)
    url: str = Field(min_length=2, max_length=1000)
    enabled: bool = True
    language: str | None = Field(default=None, max_length=10)


class SourceUpdate(BaseModel):
    type: SourceType | None = None
    name: str | None = Field(default=None, min_length=2, max_length=200)
    url: str | None = Field(default=None, min_length=2, max_length=1000)
    enabled: bool | None = None
    language: str | None = Field(default=None, max_length=10)


class SourceRead(SourceCreate, ORMModel):
    id: int
    created_at: datetime


class KeywordCreate(BaseModel):
    word: str = Field(min_length=1, max_length=100)
    enabled: bool = True


class KeywordUpdate(BaseModel):
    word: str | None = Field(default=None, min_length=1, max_length=100)
    enabled: bool | None = None


class KeywordRead(KeywordCreate, ORMModel):
    id: int


class NewsCreate(BaseModel):
    title: str = Field(min_length=2, max_length=500)
    url: str | None = None
    summary: str = Field(min_length=2)
    source: str = Field(min_length=1, max_length=200)
    published_at: datetime | None = None
    raw_text: str | None = None
    language: str | None = None


class NewsRead(ORMModel):
    id: str
    title: str
    url: str | None
    summary: str
    source: str
    published_at: datetime
    raw_text: str | None
    language: str | None
    is_relevant: bool
    created_at: datetime


class PostRead(ORMModel):
    id: int
    news_id: str
    generated_text: str
    status: PostStatus
    published_at: datetime | None
    telegram_message_id: int | None
    error: str | None
    created_at: datetime


class GenerateRequest(BaseModel):
    news_id: str | None = None
    text: str | None = Field(default=None, min_length=5)
    title: str | None = None


class PublishRequest(BaseModel):
    confirm: bool = False


class ErrorLogRead(ORMModel):
    id: int
    operation: str
    message: str
    created_at: datetime
