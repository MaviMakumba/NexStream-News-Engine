from fastapi import APIRouter, Depends, Query, BackgroundTasks
from typing import List, Optional

from src.infrastructure.config.database import SessionLocal
from src.adapters.repositories.news_repository import NewsRepository
from src.adapters.analysis.textblob_analyzer import TextBlobAnalyzer
from src.adapters.scrapers.bbc_scraper import BBCRssScraper
from src.application.services.news_service import NewsService
from src.domain.schemas.news_schema import NewsResponse, ScrapeCommand
from src.dependencies import get_news_service

router = APIRouter(prefix="/news", tags=["News"])

def _run_scrape(source: str):
    """Background thread'de çalışır, kendi session'ını açar."""
    from src.adapters.scrapers.bbc_scraper import BBCRssScraper

    scraper_map = {
        "BBC Technology": BBCRssScraper(),
    }
    scraper = scraper_map.get(source)
    if not scraper:
        print(f"⚠️ Bilinmeyen kaynak: {source}")
        return

    db = SessionLocal()
    try:
        repo = NewsRepository(db)
        analyzer = TextBlobAnalyzer()
        service = NewsService(repository=repo, analyzer=analyzer)
        service.update_news_from_source(scraper)
    finally:
        db.close()

@router.post("/scrape")
def trigger_scrape(
    request: ScrapeCommand,
    background_tasks: BackgroundTasks
):
    """İstenen kaynağı arka planda çeker."""
    background_tasks.add_task(_run_scrape, request.source)
    return {"status": "triggered", "source": request.source}

@router.get("/", response_model=List[NewsResponse])
def get_news(
    limit: int = Query(10),
    sentiment: Optional[str] = Query(None),
    service: NewsService = Depends(get_news_service)
):
    return service.list_news(limit, sentiment)