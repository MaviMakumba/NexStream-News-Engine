from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional


class ScrapeCommand(BaseModel):
    source: str = Field(..., min_length=1, max_length=64)


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=200)
    n_results: int = Field(default=10, ge=1, le=50)
    source: Optional[str] = Field(None, max_length=64)
    sentiment: Optional[str] = Field(None, pattern="^(Positive|Negative|Neutral)$")


class SearchResult(BaseModel):
    id: str
    title: str
    summary: str
    source: str
    url: str
    score: float


class NewsResponse(BaseModel):
    id: int
    title: str
    source: str
    url: str
    content: Optional[str] = None
    summary: Optional[str] = None
    sentiment_label: Optional[str] = None
    sentiment_score: Optional[float] = None
    created_at: datetime

    model_config = {"from_attributes": True}
