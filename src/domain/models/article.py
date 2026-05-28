from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

@dataclass
class Article:
    title: str
    source: str
    url: str
    content: str
    summary: Optional[str] = None
    sentiment_score: Optional[float] = None
    sentiment_label: Optional[str] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    published_at: Optional[datetime] = None
    entities: Optional[dict] = None
    topic: Optional[str] = None
    is_duplicate: bool = False
    quality_score: Optional[float] = None
    credibility_score: Optional[float] = None
    corroboration_count: int = 0
    id: Optional[int] = None