from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class NewsResponse(BaseModel):
    id: int
    title: str
    source: str
    url: str
    created_at: datetime
    
    # Yeni Yapay Zeka Alanları
    summary: Optional[str] = None
    sentiment_label: Optional[str] = None
    sentiment_score: Optional[float] = None

    class Config:
        from_attributes = True  # ORM nesnesini Pydantic'e çevirmek için şart