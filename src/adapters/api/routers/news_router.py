from fastapi import APIRouter, Depends, Query, Request, HTTPException
from typing import List, Optional
import json

from src.domain.schemas.news_schema import NewsResponse, ScrapeCommand
from src.application.services.news_service import NewsService
from src.dependencies import get_news_service

router = APIRouter(prefix="/news", tags=["News"])

@router.post("/scrape")
async def trigger_scrape(request_body: ScrapeCommand, request: Request):
    """İstenen kaynağı çekmesi için KAFKA'ya emir fırlatır (Gerçek Event-Driven)."""
    try:
        # main.py'de uygulama state'ine koyduğumuz Kafka Producer'ı alıyoruz
        producer = request.app.state.kafka_producer
        
        # Emri Kafka'nın anlayacağı byte formatına çevir
        message_bytes = json.dumps(request_body.model_dump()).encode("utf-8")
        
        # Haberi 'news_updates' bandına at ve hemen müşteriye dön!
        await producer.send_and_wait("news_updates", message_bytes)
        
        return {"status": "triggered", "source": request_body.source, "message": "Emir Kafka kuyruğuna alındı."}
    
    except AttributeError:
        raise HTTPException(status_code=500, detail="Kafka Producer bulunamadı. main.py'yi kontrol et.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Kafka İletişim Hatası: {str(e)}")

@router.get("/", response_model=List[NewsResponse])
def get_news(
    limit: int = Query(10),
    sentiment: Optional[str] = Query(None),
    service: NewsService = Depends(get_news_service)
):
    return service.list_news(limit, sentiment)