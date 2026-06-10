"""Haber kaynağı port'u — "haber çekebilen bir şey" sözleşmesi.

Somut implementasyonlar adapters/scrapers/rss_scrapers.py'dedir; yeni kaynak
eklemek registry'ye bir kayıt eklemekten ibarettir, domain değişmez.
"""

from abc import ABC, abstractmethod
from typing import List
from src.domain.models.article import Article

class NewsScraperPort(ABC):

    @abstractmethod
    async def fetch_news(self) -> List[Article]:
        pass
