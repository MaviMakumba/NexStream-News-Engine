"""API istek/yanıt şemaları (Pydantic).

Domain dataclass'ları iç dünyada, bu şemalar HTTP sınırında yaşar:
validasyon kuralları (uzunluk, pattern) burada uygulanır.
"""

from pydantic import BaseModel, Field
from datetime import datetime
from typing import List, Optional


class ScrapeCommand(BaseModel):
    source: str = Field(..., min_length=1, max_length=64)


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=200)
    # Üst sınır Enterprise tavanı (bkz. TIER_SEARCH_RESULT_CAP) — asıl tier'a göre
    # kısıtlama endpoint'te uygulanır (search_news_v1/search_news), burası sadece
    # şema seviyesinde kaba bir üst sınır.
    n_results: int = Field(default=10, ge=1, le=200)
    source: Optional[str] = Field(None, max_length=64)
    sentiment: Optional[str] = Field(None, pattern="^(Positive|Negative|Neutral)$")


class SearchResult(BaseModel):
    id: str
    title: str
    summary: str
    source: str
    url: str
    score: float
    created_at: Optional[datetime] = None


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
    published_at: Optional[datetime] = None
    entities: Optional[dict] = None
    topic: Optional[str] = None
    is_duplicate: bool = False
    quality_score: Optional[float] = None
    credibility_score: Optional[float] = None
    corroboration_count: int = 0

    model_config = {"from_attributes": True}


class NewsPage(BaseModel):
    items: List[NewsResponse]
    next_cursor: Optional[int] = None
    count: int


class TrendingEntity(BaseModel):
    name: str
    count: int
    type: str
    example_titles: list[str] = Field(default_factory=list)


class TrendingResponse(BaseModel):
    hours: int
    entities: list[TrendingEntity]


class RelatedArticle(BaseModel):
    id: int
    title: str
    source: str
    url: str
    topic: Optional[str] = None
    shared_entities: List[str] = Field(default_factory=list)
    overlap: int


class RelatedResponse(BaseModel):
    article_id: int
    related: List[RelatedArticle] = Field(default_factory=list)


# v2.2 — story cluster ("bu haberi kim nasıl anlatıyor"). `related`'dan farkı:
# entity kesişimi değil semantik vektör benzerliği (aynı OLAY, farklı kaynak).
class StorySource(BaseModel):
    id: int
    title: str
    source: str
    url: str
    score: float


class StoryClusterResponse(BaseModel):
    article_id: int
    sources: List[StorySource] = Field(default_factory=list)
