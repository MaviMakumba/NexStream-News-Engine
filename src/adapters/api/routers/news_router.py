from fastapi import APIRouter, Depends, Query, HTTPException, Request
from typing import List, Optional

from src.domain.schemas.news_schema import NewsResponse, ScrapeCommand, SearchRequest, SearchResult, TrendingResponse
from src.domain.ports.messaging_port import MessagePublisherPort
from src.application.services.news_service import NewsService
from src.dependencies import get_news_service, get_message_publisher
from src.adapters.api.auth import verify_api_key
from src.adapters.api.limiter import limiter

router = APIRouter(prefix="/news", tags=["News"])


@router.post("/scrape")
@limiter.limit("6/minute")
async def trigger_scrape(
    request: Request,
    body: ScrapeCommand,
    publisher: MessagePublisherPort = Depends(get_message_publisher),
    _: None = Depends(verify_api_key),
):
    success = await publisher.publish("news_updates", body.model_dump())
    if not success:
        raise HTTPException(status_code=500, detail="Mesaj kuyruğa iletilemedi.")
    return {"status": "triggered", "source": body.source, "message": "Emir kuyruğa alındı."}


@router.get("/", response_model=List[NewsResponse])
@limiter.limit("120/minute")
def get_news(
    request: Request,
    limit: int = Query(10),
    sentiment: Optional[str] = Query(None),
    service: NewsService = Depends(get_news_service),
):
    return service.list_news(limit, sentiment)


@router.post("/search", response_model=List[SearchResult])
@limiter.limit("30/minute")
def search_news(
    request: Request,
    body: SearchRequest,
    service: NewsService = Depends(get_news_service),
):
    return service.hybrid_search(body.query, body.n_results, body.source, body.sentiment)


@router.get("/trending", response_model=TrendingResponse)
@limiter.limit("30/minute")
def get_trending(
    request: Request,
    hours: int = Query(6, ge=1, le=72),
    limit: int = Query(10, ge=1, le=30),
    service: NewsService = Depends(get_news_service),
):
    return service.get_trending(hours, limit)


@router.post("/reanalyze")
@limiter.limit("2/minute")
def reanalyze_all(
    request: Request,
    service: NewsService = Depends(get_news_service),
    _: None = Depends(verify_api_key),
):
    return service.reanalyze_all()


@router.post("/reindex")
async def reindex_all(
    service: NewsService = Depends(get_news_service),
    _: None = Depends(verify_api_key),
):
    return service.reindex_all()


@router.get("/sources")
def get_sources():
    from src.adapters.scrapers.registry import SCRAPER_REGISTRY
    return list(SCRAPER_REGISTRY.keys())
