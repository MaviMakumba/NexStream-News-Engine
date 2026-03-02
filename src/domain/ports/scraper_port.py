from abc import ABC, abstractmethod
from typing import List
from src.domain.models.article import Article

class NewsScraperPort(ABC):

    @abstractmethod
    def fetch_news(self) -> List[Article]:
        """
        Geriye Article listesi döner.
        Her scraper bu sözleşmeye uymak zorundadır.
        """
        pass