from abc import ABC, abstractmethod
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