import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock
from src.adapters.notifications.websocket_notifier import WebSocketNotifier
from src.domain.models.article import Article
from datetime import datetime, timezone


def make_article(article_id=1):
    return Article(
        id=article_id,
        title="Test Haber",
        source="TRT Haber",
        url=f"https://trthaber.com/{article_id}",
        content="İçerik",
        summary="Özet",
        sentiment_label="Positive",
        topic="Technology",
        created_at=datetime(2026, 5, 26, 12, 0, tzinfo=timezone.utc),
    )


@pytest.mark.asyncio
async def test_connect_adds_to_pool():
    notifier = WebSocketNotifier()
    ws = AsyncMock()
    await notifier.connect(ws)
    assert notifier.connection_count == 1
    ws.accept.assert_called_once()


@pytest.mark.asyncio
async def test_disconnect_removes_from_pool():
    notifier = WebSocketNotifier()
    ws = AsyncMock()
    await notifier.connect(ws)
    notifier.disconnect(ws)
    assert notifier.connection_count == 0


@pytest.mark.asyncio
async def test_broadcast_article_sends_json():
    notifier = WebSocketNotifier()
    ws = AsyncMock()
    await notifier.connect(ws)

    article = make_article(42)
    await notifier.broadcast_article(article)

    ws.send_json.assert_called_once()
    payload = ws.send_json.call_args[0][0]
    assert payload["type"] == "article"
    assert payload["data"]["id"] == 42
    assert payload["data"]["title"] == "Test Haber"
    assert payload["data"]["source"] == "TRT Haber"


@pytest.mark.asyncio
async def test_broadcast_no_connections_no_send():
    notifier = WebSocketNotifier()
    article = make_article()
    await notifier.broadcast_article(article)  # should not raise


@pytest.mark.asyncio
async def test_broadcast_dead_connection_removed():
    notifier = WebSocketNotifier()
    ws = AsyncMock()
    ws.send_json.side_effect = Exception("bağlantı koptu")
    await notifier.connect(ws)

    article = make_article()
    await notifier.broadcast_article(article)

    assert notifier.connection_count == 0


@pytest.mark.asyncio
async def test_broadcast_multiple_clients():
    notifier = WebSocketNotifier()
    ws1 = AsyncMock()
    ws2 = AsyncMock()
    await notifier.connect(ws1)
    await notifier.connect(ws2)

    await notifier.broadcast_article(make_article())

    ws1.send_json.assert_called_once()
    ws2.send_json.assert_called_once()
