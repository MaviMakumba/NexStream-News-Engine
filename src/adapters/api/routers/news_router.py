from fastapi import APIRouter, Depends, Query, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional

# --- GEREKLİ MODÜLLER ---
from src.infrastructure.config.database import get_db
from src.adapters.repositories.news_repository import NewsRepository
from src.application.services.news_service import NewsService
from src.domain.schemas.news_schema import NewsResponse 
# Unutulan Robot Import'u:
from src.adapters.scrapers.bbc_scraper import BBCRssScraper

router = APIRouter(
    prefix="/news",
    tags=["News"],
    responses={404: {"description": "Not found"}},
)

# --- İŞTE EKSİK OLAN YEŞİL BUTON (POST) ---
@router.post("/update-bbc")
def update_news(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    BBC'den haberleri çeker ve veritabanına kaydeder (Tetikleyici).
    """
    # 1. Ekibi Kur
    repository = NewsRepository(db)
    service = NewsService(repository)
    scraper = BBCRssScraper()
    
    # 2. İşi Arka Plana At (API donmasın diye)
    background_tasks.add_task(service.update_news_from_source, scraper)
    
    return {"status": "triggered", "message": "BBC güncellemesi arka planda başlatıldı."}

# --- MEVCUT MAVİ BUTON (GET) ---
@router.get("/", response_model=List[NewsResponse])
def get_news(
    limit: int = Query(10, description="Kaç haber getirilsin?"),
    sentiment: Optional[str] = Query(None, description="Filtre: Positive, Negative, Neutral"),
    db: Session = Depends(get_db)
):
    """
    Veritabanındaki son analiz edilmiş haberleri listeler.
    """
    repository = NewsRepository(db)
    service = NewsService(repository)
    
    return service.list_news(limit, sentiment)