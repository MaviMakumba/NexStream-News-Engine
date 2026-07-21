from unittest.mock import MagicMock

from src.domain.models.user import User, UserTier
from src.adapters.api.auth_utils import check_tier_limit


def _override(app_client, mock_service):
    from src.dependencies import get_news_service
    app_client.app.dependency_overrides[get_news_service] = lambda: mock_service


def _override_pro(app_client, mock_service):
    """/api/v1'deki ilişki grafı Pro+ gerektirir (v1.14 tier-gating)."""
    _override(app_client, mock_service)
    pro = User(id=1, email="pro@test.com", password_hash="h", tier=UserTier.PRO)
    app_client.app.dependency_overrides[check_tier_limit] = lambda: pro


def _clear(app_client):
    app_client.app.dependency_overrides.clear()


_PAYLOAD = {
    "article_id": 1,
    "related": [
        {"id": 2, "title": "İlgili haber", "source": "BBC", "url": "u2",
         "topic": "Technology", "shared_entities": ["Erdogan"], "overlap": 1},
    ],
}


def test_related_endpoint_returns_payload(app_client):
    """Güvenlik denetimi (v1.17): legacy /news/{id}/related da artık Pro+ ister
    — /api/v1 ile aynı kilit, herhangi bir tier atlatma yolu kalmadı."""
    mock_service = MagicMock()
    mock_service.get_related.return_value = _PAYLOAD
    _override_pro(app_client, mock_service)
    try:
        r = app_client.get("/news/1/related")
    finally:
        _clear(app_client)

    assert r.status_code == 200
    data = r.json()
    assert data["article_id"] == 1
    assert data["related"][0]["id"] == 2
    assert data["related"][0]["overlap"] == 1


def test_related_endpoint_blocked_for_free_tier(app_client):
    mock_service = MagicMock()
    _override(app_client, mock_service)
    free = User(id=1, email="free@test.com", password_hash="h", tier=UserTier.FREE)
    app_client.app.dependency_overrides[check_tier_limit] = lambda: free
    try:
        r = app_client.get("/news/1/related")
    finally:
        _clear(app_client)
    assert r.status_code == 403


def test_related_endpoint_blocked_for_anonymous(app_client):
    mock_service = MagicMock()
    _override(app_client, mock_service)
    app_client.app.dependency_overrides[check_tier_limit] = lambda: None
    try:
        r = app_client.get("/news/1/related")
    finally:
        _clear(app_client)
    assert r.status_code == 403


def test_related_endpoint_passes_limit(app_client):
    mock_service = MagicMock()
    mock_service.get_related.return_value = {"article_id": 1, "related": []}
    _override_pro(app_client, mock_service)
    try:
        app_client.get("/news/1/related?limit=8")
    finally:
        _clear(app_client)

    mock_service.get_related.assert_called_once_with(1, 8)


def test_related_endpoint_default_limit(app_client):
    mock_service = MagicMock()
    mock_service.get_related.return_value = {"article_id": 5, "related": []}
    _override_pro(app_client, mock_service)
    try:
        app_client.get("/news/5/related")
    finally:
        _clear(app_client)

    mock_service.get_related.assert_called_once_with(5, 5)


def test_related_v1_endpoint(app_client):
    mock_service = MagicMock()
    mock_service.get_related.return_value = _PAYLOAD
    _override_pro(app_client, mock_service)
    try:
        r = app_client.get("/api/v1/news/1/related")
    finally:
        _clear(app_client)

    assert r.status_code == 200
    assert r.json()["related"][0]["id"] == 2


def test_related_endpoint_rejects_non_integer_id(app_client):
    r = app_client.get("/news/abc/related")
    assert r.status_code == 422
