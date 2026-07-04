from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


class KBArticleBase(BaseModel):
    title: str = Field(..., min_length=5, max_length=200)
    content: str = Field(..., min_length=20)
    category: str = Field(..., min_length=2, max_length=50)
    tags: List[str] = []


class KBArticleCreate(KBArticleBase):
    pass


class KBArticleUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    category: Optional[str] = None
    tags: Optional[List[str]] = None


class KBArticleInDBBase(KBArticleBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class KBArticle(KBArticleInDBBase):
    pass


class KBSearchResult(BaseModel):
    article: KBArticle
    score: float


class KBChunk(BaseModel):
    id: int
    content: str
    metadata: dict  # source, page, type


class KBSearchQuery(BaseModel):
    query: str = Field(..., min_length=1, max_length=500, description="The query string to search.")
    top_k: int = Field(4, ge=1, le=20, description="The maximum number of matching segments to return.")

