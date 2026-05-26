import logging
from fastapi import WebSocket
from src.domain.ports.notification_port import NotificationPort
from src.domain.models.article import Article

logger = logging.getLogger(__name__)


class WebSocketNotifier(NotificationPort):
    def __init__(self):
        self._connections: set[WebSocket] = set()

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self._connections.add(websocket)
        logger.info("WebSocket bağlandı. Aktif: %d", len(self._connections))

    def disconnect(self, websocket: WebSocket) -> None:
        self._connections.discard(websocket)
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
