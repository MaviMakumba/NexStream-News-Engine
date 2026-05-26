from abc import ABC, abstractmethod
from src.domain.models.article import Article


class NotificationPort(ABC):
    @abstractmethod
    async def broadcast_article(self, article: Article) -> None:
        pass
