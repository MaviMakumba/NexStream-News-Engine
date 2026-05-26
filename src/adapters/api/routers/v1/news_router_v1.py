import time
from fastapi import APIRouter, Depends, Query, Request
from typing import Optional

from src.domain.schemas.news_schema import NewsPage, SearchRequest, SearchResult, TrendingResponse
from src.application.services.news_service import NewsService
from src.dependencies import get_news_service
from src.adapters.api.limiter import limiter
from src.adapters.api.metrics import search_latency_seconds

router = APIRouter(prefix="/api/v1", tags=["API v1"])


@router.get("/news", response_model=NewsPage)
@limiter.limit("120/minute")
def get_news_v1(
    request: Request,
    limit: int = Query(20, ge=1, le=100, description="Sayfa başına haber sayısı"),
    cursor: Optional[int] = Query(None, description="Önceki sayfanın son haber ID'si (cursor-based pagination)"),
    source: Optional[str] = Query(None, max_length=64),
    sentiment: Optional[str] = Query(None, pattern="^(Positive|Negative|Neutral)$"),
    topic: Optional[str] = Query(None, max_length=32),
    service: NewsService = Depends(get_news_service),
):
    """
    Cursor-based paginated news list.
    İlk sayfa: cursor yok. Sonraki sayfa: önceki yanıttaki next_cursor değerini cursor olarak gönder.
    next_cursor null ise daha fazla haber yok.
    """
    items = service.list_news_paginated(limit + 1, cursor, source, sentiment, topic)
    next_cursor = items[limit].id if len(items) > limit else None
    page_items = items[:limit]
    return NewsPage(items=page_items, next_cursor=next_cursor, count=len(page_items))


@router.post("/news/search", response_model=list[SearchResult])
@limiter.limit("30/minute")
def search_news_v1(
    request: Request,
    body: SearchRequest,
    service: NewsService = Depends(get_news_service),
):
    start = time.time()
    results = service.hybrid_search(body.query, body.n_results, body.source, body.sentiment)
    search_latency_seconds.observe(time.time() - start)
    return results


@router.get("/news/trending", response_model=TrendingResponse)
@limiter.limit("30/minute")
def get_trending_v1(
    request: Request,
    hours: int = Query(6, ge=1, le=72),
    limit: int = Query(10, ge=1, le=30),
    service: NewsService = Depends(get_news_service),
):
    return service.get_trending(hours, limit)


@router.get("/news/sources")
def get_sources_v1():
    from src.adapters.scrapers.registry import SCRAPER_REGISTRY
    return list(SCRAPER_REGISTRY.keys())
