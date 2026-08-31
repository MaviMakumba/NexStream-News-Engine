"""Article — sistemin merkezi domain modeli.

Scraper üretir, analyzer zenginleştirir (summary/sentiment/entities/topic),
scoring puanlar (quality/credibility), repository kalıcılaştırır, API sunar.
Saf dataclass'tır: ORM ve Pydantic karşılıkları adapter katmanındadır.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

from src.domain.scoring.trust import compute_trust_score, trust_score_breakdown

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

    @property
    def trust_score(self) -> int:
        """0-100 görünür güven skoru — okuma anında hesaplanır, saklanmaz
        (bkz. `compute_trust_score` docstring'i: corroboration_count zamanla
        artabilir, saklanan bir değer bu durumda bayatlar)."""
        return compute_trust_score(self.quality_score, self.credibility_score, self.corroboration_count)

    @property
    def trust_breakdown(self) -> dict:
        """`trust_score`'un hangi bileşenden kaç puan geldiği — NewsCard'ın
        güven rozeti hover metninde haber-başına gerçek sayı göstermek için."""
        return trust_score_breakdown(self.quality_score, self.credibility_score, self.corroboration_count)