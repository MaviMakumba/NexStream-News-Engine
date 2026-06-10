"""Canlı bildirim port'u — yeni haberi bağlı istemcilere duyurma sözleşmesi.

Somut implementasyon: WebSocketNotifier (/ws/feed bağlantılarına broadcast).
"""

from abc import ABC, abstractmethod
from src.domain.models.article import Article


class NotificationPort(ABC):
    @abstractmethod
    async def broadcast_article(self, article: Article) -> None:
        pass
