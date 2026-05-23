from abc import ABC, abstractmethod
from typing import List
from src.domain.models.article import Article

class NewsScraperPort(ABC):

    @abstractmethod
    async def fetch_news(self) -> List[Article]:
        pass
