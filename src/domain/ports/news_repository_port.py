"""Haber repository port'u — kalıcı haber deposu sözleşmesi.

Somut implementasyon: adapters/repositories/news_repository.py (PostgreSQL).
"""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Optional
from src.domain.models.article import Article

class NewsRepositoryPort(ABC):
    """Veritabanı için sözleşme. Hangi DB olursa olsun bu kurallara uyacak."""
    
    @abstractmethod
    def save_article(self, article: Article) -> bool:
        pass
        
    @abstractmethod
    def get_latest_news(self, limit: int, sentiment_filter: Optional[str] = None) -> List[Article]:
        pass
        
    @abstractmethod
    def article_exists(self, url: str) -> bool:
        pass

    @abstractmethod
    def get_all_articles(self) -> List[Article]:
        pass

    @abstractmethod
    def keyword_search(self, query: str, limit: int = 10, source: Optional[str] = None, sentiment: Optional[str] = None) -> List[Article]:
        pass

    @abstractmethod
    def bulk_exists(self, urls: list[str]) -> set[str]:
        pass

    @abstractmethod
    def delete_articles_before(self, cutoff: datetime) -> int:
        """KALICI silme — yalnızca `db_retention_days` açıkça ayarlıysa çağrılır."""
        pass

    @abstractmethod
    def get_articles_created_after(self, cutoff: datetime) -> List[Article]:
        """Entity şartı olmadan tarih filtresi — retention job'un self-healing reindex'i için."""
        pass