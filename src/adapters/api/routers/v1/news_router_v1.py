"""Public API v1 (/api/v1) — dış tüketiciler için sürümlü, kotalı haber API'si.

/news router'ından farkları:
    * Sürümlüdür — kırıcı değişiklik v2'ye gider, v1 sözleşmesi korunur
    * Cursor-based pagination (offset yerine id imleci → tutarlı sayfalama)
    * check_tier_limit ile günlük kota: Free 100 / Pro 2000 / Enterprise sınırsız
    * Kullanımı usage_tracking_middleware loglar (kota sayacının kaynağı)

Kimlik: X-Session-Token (web) veya X-User-Key (kişisel API anahtarı, v1.11).
Anonim erişim serbesttir ama kota takibi yapılmaz, sadece IP rate limit uygulanır.
"""

import time
from fastapi import APIRouter, Depends, Query, Request
from typing import Optional

from src.domain.schemas.news_schema import NewsPage, SearchRequest, SearchResult, TrendingResponse, RelatedResponse
from src.application.services.news_service import NewsService
from src.dependencies import get_news_service
from src.adapters.api.limiter import limiter
from src.adapters.api.metrics import search_latency_seconds
from src.adapters.api.auth_utils import check_tier_limit
from src.adapters.scrapers.registry import SCRAPER_REGISTRY

router = APIRouter(prefix="/api/v1", tags=["API v1"], dependencies=[Depends(check_tier_limit)])


@router.get("/news", response_model=NewsPage)
@limiter.limit("120/minute")
def get_news_v1(
    request: Request,
    limit: int = Query(20, ge=1, le=100, description="Sayfa başına haber sayısı"),
    cursor: Optional[int] = Query(None, description="Önceki sayfanın son haber ID'si (cursor-based pagination)"),
    source: Optional[str] = Query(None, max_length=64),
    sentiment: Optional[str] = Query(None, pattern="^(Positive|Negative|Neutral)$"),
    topic: Optional[str] = Query(None, max_length=32),
    min_quality: Optional[float] = Query(None, ge=0.0, le=1.0, description="Sadece bu kalite skorunun üzerindeki haberler"),
    service: NewsService = Depends(get_news_service),
):
    """Cursor-based sayfalı haber listesi.

    İlk sayfa: cursor gönderme. Sonraki sayfa: önceki yanıttaki next_cursor'ı
    cursor olarak gönder. next_cursor null ise daha fazla haber yok.
    """
    # limit+1 çekilir: fazladan kayıt varsa bir sonraki sayfa var demektir.
    items = service.list_news_paginated(limit + 1, cursor, source, sentiment, topic, min_quality)
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
    """Hybrid arama: ChromaDB semantik + PostgreSQL keyword birleşimi."""
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
    """Son N saatin en sık geçen entity'leri (gündem)."""
    return service.get_trending(hours, limit)


@router.get("/news/sources")
def get_sources_v1():
    """Sistemdeki aktif haber kaynaklarının listesi."""
    return list(SCRAPER_REGISTRY.keys())


@router.get("/news/{article_id}/related", response_model=RelatedResponse)
@limiter.limit("60/minute")
def get_related_v1(
    request: Request,
    article_id: int,
    limit: int = Query(5, ge=1, le=20),
    service: NewsService = Depends(get_news_service),
):
    """Entity kesişimine göre ilgili haberler (ilişki grafı)."""
    return service.get_related(article_id, limit)
