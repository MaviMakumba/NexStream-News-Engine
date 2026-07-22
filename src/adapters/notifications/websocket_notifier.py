"""WebSocket canlı yayın adapter'ı — /ws/feed istemcilerine haber push'lar.

Bağlantı seti bellektedir (tek instance varsayımı); gönderim hatası alan
bağlantılar otomatik düşürülür. v1.18: tek bir kullanıcının (veya toplamda)
sınırsız bağlantı açıp belleği/CPU'yu tüketmesine karşı per-user + global
bağlantı tavanı — `can_accept()` router tarafından accept'ten ÖNCE sorulur.
"""

import logging
from typing import Optional
from fastapi import WebSocket
from src.domain.ports.notification_port import NotificationPort
from src.domain.models.article import Article

logger = logging.getLogger(__name__)


class WebSocketNotifier(NotificationPort):
    def __init__(self, max_per_user: int = 5, max_total: int = 500):
        self._connections: set[WebSocket] = set()
        self._by_user: dict[str, set[WebSocket]] = {}
        self._max_per_user = max_per_user
        self._max_total = max_total

    def can_accept(self, user_key: Optional[str]) -> bool:
        """Router accept()'ten önce çağırır — limit aşılıyorsa bağlantı reddedilir."""
        if len(self._connections) >= self._max_total:
            return False
        if user_key and len(self._by_user.get(user_key, ())) >= self._max_per_user:
            return False
        return True

    async def connect(self, websocket: WebSocket, user_key: Optional[str] = None) -> None:
        await websocket.accept()
        self._connections.add(websocket)
        if user_key:
            self._by_user.setdefault(user_key, set()).add(websocket)
        logger.info("WebSocket bağlandı. Aktif: %d", len(self._connections))

    def disconnect(self, websocket: WebSocket) -> None:
        self._connections.discard(websocket)
        for conns in self._by_user.values():
            conns.discard(websocket)
        logger.info("WebSocket ayrıldı. Aktif: %d", len(self._connections))

    @property
    def connection_count(self) -> int:
        return len(self._connections)

    async def broadcast_article(self, article: Article) -> None:
        if not self._connections:
            return
        payload = {
            "type": "article",
            "data": {
                "id": article.id,
                "title": article.title,
                "source": article.source,
                "url": article.url,
                "summary": article.summary or "",
                "sentiment_label": article.sentiment_label,
                "topic": article.topic,
                "created_at": article.created_at.isoformat() if article.created_at else None,
            },
        }
        dead: set[WebSocket] = set()
        for ws in list(self._connections):
            try:
                await ws.send_json(payload)
            except Exception:
                dead.add(ws)
        for ws in dead:
            self.disconnect(ws)
