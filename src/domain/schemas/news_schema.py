from pydantic import BaseModel
from datetime import datetime
from typing import Optional

# 1. EMİR ŞEMASI (Request / Command)
# İleride Kafka'ya gönderirken veya API'den alırken bu standardı kullanacağız.
class ScrapeCommand(BaseModel):
    source: str

# 2. YANIT ŞEMASI (Response)
# API'den kullanıcıya (veya Frontend'e) dönecek olan veri formatı.
class NewsResponse(BaseModel):
    id: int
    title: str
    source: str
    url: str
    content: Optional[str] = None  # Bilge mimarın uyarısı: Artık içeriği de gösteriyoruz
    summary: Optional[str] = None
    sentiment_label: Optional[str] = None
    sentiment_score: Optional[float] = None
    created_at: datetime

    # Pydantic v2 için doğru konfigürasyon (Eskiden class Config: from_attributes = True idi)
    model_config = {"from_attributes": True}