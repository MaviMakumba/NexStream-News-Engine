"""GET /news/{id}/sources ve /api/v1/news/{id}/sources testleri (v2.2, story cluster).

`related` (Pro+, entity kesişimi) ile aynı router deseni ama tier gating YOK
— corroboration rozeti gibi bir şeffaflık özelliği, herkese açık.
"""

from unittest.mock import MagicMock


def _override(app_client, mock_service):
    from src.dependencies import get_news_service
    app_client.app.dependency_overrides[get_news_service] = lambda: mock_service


def _clear(app_client):
    app_client.app.dependency_overrides.clear()


_PAYLOAD = {
    "article_id": 1,
    "sources": [{"id": 2, "title": "Başka kaynak", "source": "TRT", "url": "u2", "score": 0.81}],
}


def test_story_cluster_endpoint_returns_payload_anonymous(app_client):
    """Free/gating yok — anonim istek bile 200 dönmeli (related'ın aksine)."""
    mock_service = MagicMock()
    mock_service.get_story_cluster.return_value = _PAYLOAD
    _override(app_client, mock_service)
    try:
        r = app_client.get("/news/1/sources")
    finally:
        _clear(app_client)

    assert r.status_code == 200
    data = r.json()
    assert data["article_id"] == 1
    assert data["sources"][0]["source"] == "TRT"


def test_story_cluster_endpoint_passes_limit(app_client):
    mock_service = MagicMock()
    mock_service.get_story_cluster.return_value = {"article_id": 1, "sources": []}
    _override(app_client, mock_service)
    try:
        app_client.get("/news/1/sources?limit=3")
    finally:
        _clear(app_client)

    mock_service.get_story_cluster.assert_called_once_with(1, 3)


def test_story_cluster_endpoint_default_limit(app_client):
    mock_service = MagicMock()
    mock_service.get_story_cluster.return_value = {"article_id": 5, "sources": []}
    _override(app_client, mock_service)
    try:
        app_client.get("/news/5/sources")
    finally:
        _clear(app_client)

    mock_service.get_story_cluster.assert_called_once_with(5, 6)


def test_story_cluster_endpoint_rejects_non_integer_id(app_client):
    r = app_client.get("/news/abc/sources")
    assert r.status_code == 422


def test_story_cluster_v1_endpoint(app_client):
    mock_service = MagicMock()
    mock_service.get_story_cluster.return_value = _PAYLOAD
    _override(app_client, mock_service)
    try:
        r = app_client.get("/api/v1/news/1/sources")
    finally:
        _clear(app_client)

    assert r.status_code == 200
    assert r.json()["sources"][0]["id"] == 2
