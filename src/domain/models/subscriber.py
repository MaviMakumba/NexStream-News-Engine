"""Newsletter abonesi domain modeli.

frequency alanı teslimat modunu belirler: "daily" (günlük digest),
"instant" (keyword eşleşmesinde anında alert), "never" (durduruldu).
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional


@dataclass
class Subscriber:
    email: str
    keywords: List[str] = field(default_factory=list)
    preferred_sources: List[str] = field(default_factory=list)
    preferred_topics: List[str] = field(default_factory=list)
    language: str = "TR"
    frequency: str = "daily"   # "daily" | "instant" | "never"
    is_active: bool = True
    id: Optional[int] = None
    created_at: Optional[datetime] = None
