import pytest
from unittest.mock import MagicMock
from src.domain.models.article import Article
from datetime import datetime, timezone


def make_article(article_id: int):
    return Article(
        id=article_id,
        title=f"Haber {article_id}",
        source="TRT Haber",
        url=f"https://trthaber.com/{article_id}",
        content="İçerik",
        summary="Özet",
        sentiment_label="Positive",
        sentiment_score=0.7,
        topic="Technology",
        created_at=datetime(2026, 5, 26, tzinfo=timezone.utc),
    )


def _override(app_client, mock_service):
    from src.dependencies import get_news_service
    app_client.app.dependency_overrides[get_news_service] = lambda: mock_service


def _clear(app_client):
    app_client.app.dependency_overrides.clear()


def test_v1_news_first_page(app_client):
    articles = [make_article(i) for i in range(10, 0, -1)]
    mock_service = MagicMock()
    mock_service.list_news_paginated.return_value = articles
    _override(app_client, mock_service)
    try:
        r = app_client.get("/api/v1/news?limit=10")
    finally:
        _clear(app_client)

    assert r.status_code == 200
    data = r.json()
    assert "items" in data
    assert "next_cursor" in data
    assert "count" in data


def test_v1_news_page_fields(app_client):
    articles = [make_article(i) for i in range(5, 0, -1)]
    mock_service = MagicMock()
    mock_service.list_news_paginated.return_value = articles
    _override(app_client, mock_service)
    try:
        r = app_client.get("/api/v1/news?limit=5")
    finally:
        _clear(app_client)

    data = r.json()
    assert data["count"] == 5
    # service returned exactly limit items → no next page
    assert data["next_cursor"] is None
    assert len(data["items"]) == 5


def test_v1_news_next_cursor_set_when_more(app_client):
    # service returns limit+1 items → next_cursor = item[limit].id
    articles = [make_article(i) for i in range(11, 0, -1)]
    mock_service = MagicMock()
    mock_service.list_news_paginated.return_value = articles
    _override(app_client, mock_service)
    try:
        r = app_client.get("/api/v1/news?limit=10")
    finally:
        _clear(app_client)

    data = r.json()
    assert data["next_cursor"] == articles[10].id
    assert data["count"] == 10
    assert len(data["items"]) == 10


def test_v1_news_cursor_passed_to_service(app_client):
    mock_service = MagicMock()
    mock_service.list_news_paginated.return_value = []
    _override(app_client, mock_service)
    try:
        app_client.get("/api/v1/news?limit=5&cursor=20")
    finally:
        _clear(app_client)

    mock_service.list_news_paginated.assert_called_once_with(6, 20, None, None, None)


def test_v1_news_filters_passed_to_service(app_client):
    mock_service = MagicMock()
    mock_service.list_news_paginated.return_value = []
    _override(app_client, mock_service)
    try:
        app_client.get("/api/v1/news?limit=5&source=TRT+Haber&sentiment=Positive&topic=Sports")
    finally:
        _clear(app_client)

    mock_service.list_news_paginated.assert_called_once_with(6, None, "TRT Haber", "Positive", "Sports")


def test_v1_sources(app_client):
    r = app_client.get("/api/v1/news/sources")
    assert r.status_code == 200
    sources = r.json()
    assert isinstance(sources, list)
    assert len(sources) > 0
    assert "TRT Haber" in sources
