from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

@dataclass
class Article:
    """
    Saf Domain Objesi (Entity).
    SQLAlchemy veya Pydantic BİLMEZ. Sadece bizim iş modelimizdir.
    """
    title: str
    source: str
    url: str
    content: str 
    summary: Optional[str] = None
    sentiment_score: Optional[float] = None
    sentiment_label: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    id: Optional[int] = None