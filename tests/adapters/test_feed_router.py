import pytest
from unittest.mock import MagicMock
from src.domain.models.article import Article
from datetime import datetime, timezone


def make_article(article_id: int):
    return Article(
        id=article_id,
        title=f"Test Haber {article_id}",
        source="BBC Türkçe",
        url=f"https://bbc.com/turkce/{article_id}",
        content="Haber içeriği",
        summary="Haber özeti",
        sentiment_label="Neutral",
        topic="World",
        created_at=datetime(2026, 5, 26, 10, 0, tzinfo=timezone.utc),
        published_at=datetime(2026, 5, 26, 9, 0, tzinfo=timezone.utc),
    )


def _override(app_client, mock_service):
    from src.dependencies import get_news_service
    app_client.app.dependency_overrides[get_news_service] = lambda: mock_service


def _clear(app_client):
    app_client.app.dependency_overrides.clear()


def test_rss_feed_returns_xml(app_client):
    mock_service = MagicMock()
    mock_service.list_news.return_value = [make_article(1)]
    _override(app_client, mock_service)
    try:
        r = app_client.get("/feed.xml")
    finally:
        _clear(app_client)

    assert r.status_code == 200
    assert "xml" in r.headers["content-type"]


def test_rss_feed_contains_articles(app_client):
    mock_service = MagicMock()
    mock_service.list_news.return_value = [make_article(1)]
    _override(app_client, mock_service)
    try:
        r = app_client.get("/feed.xml")
    finally:
        _clear(app_client)

    assert r.status_code == 200
    assert "Test Haber 1" in r.text
    assert "BBC" in r.text


def test_rss_feed_empty_articles(app_client):
    mock_service = MagicMock()
    mock_service.list_news.return_value = []
    _override(app_client, mock_service)
    try:
        r = app_client.get("/feed.xml")
    finally:
        _clear(app_client)

    assert r.status_code == 200
    assert "NexStream" in r.text


def test_rss_feed_calls_service_with_50(app_client):
    mock_service = MagicMock()
    mock_service.list_news.return_value = []
    _override(app_client, mock_service)
    try:
        app_client.get("/feed.xml")
    finally:
        _clear(app_client)

    mock_service.list_news.assert_called_once_with(50)
