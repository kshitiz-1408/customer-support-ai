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
