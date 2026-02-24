from fastapi import FastAPI, HTTPException
from src.adapters.repositories.news_repository import NewsRepository
from src.application.services.news_service import NewsService
from src.adapters.scrapers.bbc_scraper import BBCRssScraper

# 1. Uygulama Nesnesi (The App)
app = FastAPI(
    title="NexStream News Engine API",
    description="Haber motorunu yöneten REST API servisi.",
    version="1.0.0"
)

# 2. Bağımlılıkları Hazırla (Dependency Injection)
# Not: Gerçek projelerde bu kısım "Dependency Injection Container" ile yapılır
# ama şimdilik manuel yapıyoruz.
repo = NewsRepository()
service = NewsService(repo)
bbc_scraper = BBCRssScraper()

@app.get("/")
def health_check():
    """Sistemin ayakta olup olmadığını kontrol eder."""
    return {"status": "active", "system": "NexStream News Engine"}

@app.post("/news/update-bbc")
def trigger_bbc_update():
    """
    BBC Haberlerini manuel olarak tetikler ve günceller.
    """
    try:
        # Servisi çağırıp işi yaptırıyoruz
        service.update_news_from_source(bbc_scraper)
        return {"message": "BBC haber güncellemesi başarıyla tamamlandı."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))