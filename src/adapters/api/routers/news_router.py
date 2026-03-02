from fastapi import APIRouter, Depends, Query, HTTPException
from typing import List, Optional

from src.domain.schemas.news_schema import NewsResponse, ScrapeCommand
from src.domain.ports.messaging_port import MessagePublisherPort
from src.application.services.news_service import NewsService
from src.dependencies import get_news_service, get_message_publisher

router = APIRouter(prefix="/news", tags=["News"])

@router.post("/scrape")
async def trigger_scrape(
    request: ScrapeCommand,
    publisher: MessagePublisherPort = Depends(get_message_publisher) # 💥 KAFKA YOK, PORT VAR!
):
    """
    Sözleşme üzerinden (Port) emir yayınlar. Gerçek Event-Driven.
    """
    # Emri port üzerinden yayınla
    success = await publisher.publish("news_updates", request.model_dump())
    
    if not success:
        raise HTTPException(status_code=500, detail="Mesaj kuyruğa iletilemedi.")
        
    return {"status": "triggered", "source": request.source, "message": "Emir kuyruğa alındı."}

@router.get("/", response_model=List[NewsResponse])
def get_news(
    limit: int = Query(10),
    sentiment: Optional[str] = Query(None),
    service: NewsService = Depends(get_news_service)
):
    return service.list_news(limit, sentiment)