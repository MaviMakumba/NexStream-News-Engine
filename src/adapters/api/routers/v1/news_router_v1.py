"""Public API v1 (/api/v1) — dış tüketiciler için sürümlü, kotalı haber API'si.

/news router'ından farkları:
    * Sürümlüdür — kırıcı değişiklik v2'ye gider, v1 sözleşmesi korunur
    * Cursor-based pagination (offset yerine id imleci → tutarlı sayfalama)
    * check_tier_limit ile günlük kota: Free 100 / Pro 2000 / Enterprise sınırsız
    * Kullanımı usage_tracking_middleware loglar (kota sayacının kaynağı)

Kimlik: X-Session-Token (web) veya X-User-Key (kişisel API anahtarı, v1.11).
Anonim erişim serbesttir ama kota takibi yapılmaz, sadece IP rate limit uygulanır.
"""

import csv
import io
import json
import time
from datetime import date, datetime, time as dtime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import Response
from typing import Optional

from src.domain.schemas.news_schema import NewsPage, NewsResponse, SearchRequest, SearchResult, TrendingResponse, RelatedResponse
from src.domain.models.user import User, UserTier, TIER_SEARCH_RESULT_CAP, tier_at_least
from src.application.services.news_service import NewsService
from src.dependencies import get_news_service
from src.adapters.api.limiter import limiter
from src.adapters.api.metrics import search_latency_seconds
from src.adapters.api.auth_utils import check_tier_limit, user_effective_tier
from src.adapters.scrapers.registry import SCRAPER_REGISTRY
from src.infrastructure.config.settings import settings

router = APIRouter(prefix="/api/v1", tags=["API v1"], dependencies=[Depends(check_tier_limit)])

# Ham veri export'un hem CSV hem JSON çıktısında paylaştığı kolon sırası.
_EXPORT_FIELDS = [
    "id", "title", "source", "url", "published_at", "created_at",
    "topic", "sentiment_label", "sentiment_score", "quality_score",
    "credibility_score", "corroboration_count", "is_duplicate",
    "entities", "summary", "content",
]


def _export_row(article) -> dict:
    """JSON çıktısı için — `entities` iç içe obje olarak kalır."""
    return NewsResponse.model_validate(article).model_dump(mode="json")


def _export_csv_row(article) -> dict:
    """CSV çıktısı için — `entities` düz bir hücreye sığması için JSON string'e çevrilir."""
    row = _export_row(article)
    row["entities"] = json.dumps(row["entities"], ensure_ascii=False) if row["entities"] else ""
    return row


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
    user: Optional[User] = Depends(check_tier_limit),
    service: NewsService = Depends(get_news_service),
):
    """Hybrid arama: ChromaDB semantik + PostgreSQL keyword birleşimi.

    Sonuç sayısı kademeye göre tavanlanır (bkz. TIER_SEARCH_RESULT_CAP) —
    anonim istekler Free tavanını alır.
    """
    cap = TIER_SEARCH_RESULT_CAP[user_effective_tier(user) if user else UserTier.FREE]
    n_results = min(body.n_results, cap)
    start = time.time()
    results = service.hybrid_search(body.query, n_results, body.source, body.sentiment)
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


@router.get("/news/export")
@limiter.limit("10/minute")
def export_news_v1(
    request: Request,
    format: str = Query("csv", pattern="^(csv|json)$"),
    source: Optional[str] = Query(None, max_length=64),
    sentiment: Optional[str] = Query(None, pattern="^(Positive|Negative|Neutral)$"),
    topic: Optional[str] = Query(None, max_length=32),
    min_quality: Optional[float] = Query(None, ge=0.0, le=1.0),
    date_from: Optional[date] = Query(None, description="YYYY-MM-DD, dahil"),
    date_to: Optional[date] = Query(None, description="YYYY-MM-DD, dahil"),
    user: Optional[User] = Depends(check_tier_limit),
    service: NewsService = Depends(get_news_service),
):
    """Ham veri export — Enterprise özelliği. CSV veya JSON, filtre + tarih aralığı destekler.

    Tek istekte `settings.export_max_rows` ile sınırlanır (runaway sorgudan
    korumak için); günlük kota kontrolüne ek olarak dakikada 10 istekle
    sınırlıdır (tek export isteği yüzlerce/binlerce satıra denk gelir, diğer
    /api/v1 endpoint'leriyle karşılaştırılamaz).
    """
    if not user or user_effective_tier(user) != UserTier.ENTERPRISE:
        raise HTTPException(
            status_code=403,
            detail="Ham veri export Enterprise plan gerektirir. / Raw data export requires an Enterprise plan.",
        )
    df = datetime.combine(date_from, dtime.min, tzinfo=timezone.utc) if date_from else None
    dt = datetime.combine(date_to, dtime.max, tzinfo=timezone.utc) if date_to else None
    articles = service.export_articles(settings.export_max_rows, source, sentiment, topic, min_quality, df, dt)

    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    if format == "json":
        payload = json.dumps([_export_row(a) for a in articles], ensure_ascii=False, indent=2)
        return Response(
            content=payload,
            media_type="application/json",
            headers={"Content-Disposition": f'attachment; filename="nexstream_export_{stamp}.json"'},
        )

    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=_EXPORT_FIELDS)
    writer.writeheader()
    for article in articles:
        writer.writerow(_export_csv_row(article))
    return Response(
        # utf-8-sig (BOM'lu): Excel Türkçe karakterleri BOM'suz UTF-8 CSV'de bozuk gösterir.
        content=buf.getvalue().encode("utf-8-sig"),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="nexstream_export_{stamp}.csv"'},
    )


@router.get("/news/{article_id}/related", response_model=RelatedResponse)
@limiter.limit("60/minute")
def get_related_v1(
    request: Request,
    article_id: int,
    limit: int = Query(5, ge=1, le=20),
    user: Optional[User] = Depends(check_tier_limit),
    service: NewsService = Depends(get_news_service),
):
    """Entity kesişimine göre ilgili haberler (ilişki grafı) — Pro+ özelliği."""
    if not user or not tier_at_least(user_effective_tier(user), UserTier.PRO):
        raise HTTPException(
            status_code=403,
            detail="İlişki grafı Pro plan gerektirir. / Relation graph requires a Pro plan.",
        )
    return service.get_related(article_id, limit)
