"""/account self-service endpoint testleri (v1.11).

Kullanıcının kendi kota/kullanım panelini ve kişisel API anahtarı
yönetimini doğrular. Gerçek DB yok — repository mock'lanır.
"""

from unittest.mock import patch, MagicMock

from src.adapters.api.auth_utils import get_current_user, get_optional_user
from src.domain.models.user import User, UserTier, UserRole
from src.infrastructure.config.database import get_db


def _make_user(tier=UserTier.FREE, api_key=None, uid=1, role=UserRole.USER):
    return User(id=uid, email="me@test.com", password_hash="h", tier=tier, api_key=api_key, role=role)


def _override(app_client, user):
    app_client.app.dependency_overrides[get_current_user] = lambda: user
    app_client.app.dependency_overrides[get_optional_user] = lambda: user
    app_client.app.dependency_overrides[get_db] = lambda: MagicMock()


def _clear(app_client):
    for dep in (get_current_user, get_optional_user, get_db):
        app_client.app.dependency_overrides.pop(dep, None)


# ── /account/usage ────────────────────────────────────────────────────────────

def test_usage_requires_auth(app_client):
    resp = app_client.get("/account/usage")
    assert resp.status_code == 401


def test_usage_returns_quota_summary(app_client):
    _override(app_client, _make_user(UserTier.FREE))
    try:
        with patch("src.adapters.api.routers.account_router.UserRepository") as MockRepo:
            repo = MagicMock()
            repo.get_daily_usage_count.return_value = 37
            repo.get_usage_stats.return_value = [
                {"user_id": 1, "endpoint": "/api/v1/news", "count": 30, "avg_ms": 12.5},
                {"user_id": 1, "endpoint": "/api/v1/news/search", "count": 7, "avg_ms": 80.0},
            ]
            MockRepo.return_value = repo
            resp = app_client.get("/account/usage?days=7")
    finally:
        _clear(app_client)

    assert resp.status_code == 200
    data = resp.json()
    assert data["tier"] == "free"
    assert data["daily_limit"] == 100
    assert data["used_today"] == 37
    assert data["remaining_today"] == 63
    assert data["total_requests"] == 37
    assert len(data["by_endpoint"]) == 2


def test_usage_enterprise_has_unlimited_quota(app_client):
    _override(app_client, _make_user(UserTier.ENTERPRISE))
    try:
        with patch("src.adapters.api.routers.account_router.UserRepository") as MockRepo:
            repo = MagicMock()
            repo.get_daily_usage_count.return_value = 5000
            repo.get_usage_stats.return_value = []
            MockRepo.return_value = repo
            resp = app_client.get("/account/usage")
    finally:
        _clear(app_client)

    data = resp.json()
    assert data["daily_limit"] is None
    assert data["remaining_today"] is None


def test_usage_owner_shows_unlimited_despite_free_db_tier(app_client):
    """Owner rolü Free DB tier'ına rağmen sınırsız kota gösterir."""
    _override(app_client, _make_user(UserTier.FREE, role=UserRole.OWNER))
    try:
        with patch("src.adapters.api.routers.account_router.UserRepository") as MockRepo:
            repo = MagicMock()
            repo.get_daily_usage_count.return_value = 500
            repo.get_usage_stats.return_value = []
            MockRepo.return_value = repo
            resp = app_client.get("/account/usage")
    finally:
        _clear(app_client)

    assert resp.status_code == 200
    data = resp.json()
    assert data["daily_limit"] is None
    assert data["remaining_today"] is None


def test_usage_remaining_never_negative(app_client):
    """Kota aşılmış olsa bile remaining 0'ın altına inmez."""
    _override(app_client, _make_user(UserTier.FREE))
    try:
        with patch("src.adapters.api.routers.account_router.UserRepository") as MockRepo:
            repo = MagicMock()
            repo.get_daily_usage_count.return_value = 150
            repo.get_usage_stats.return_value = []
            MockRepo.return_value = repo
            resp = app_client.get("/account/usage")
    finally:
        _clear(app_client)

    assert resp.json()["remaining_today"] == 0


# ── /account/api-key ──────────────────────────────────────────────────────────

def test_generate_api_key_requires_auth(app_client):
    resp = app_client.post("/account/api-key")
    assert resp.status_code == 401


def test_generate_api_key_returns_prefixed_key(app_client):
    _override(app_client, _make_user())
    try:
        with patch("src.adapters.api.routers.account_router.UserRepository") as MockRepo:
            repo = MagicMock()
            repo.set_api_key.return_value = True
            MockRepo.return_value = repo
            resp = app_client.post("/account/api-key")
    finally:
        _clear(app_client)

    assert resp.status_code == 201
    key = resp.json()["api_key"]
    assert key.startswith("nxs_")
    assert len(key) > 20
    repo.set_api_key.assert_called_once()


def test_revoke_api_key_clears_key(app_client):
    _override(app_client, _make_user(api_key="nxs_old"))
    try:
        with patch("src.adapters.api.routers.account_router.UserRepository") as MockRepo:
            repo = MagicMock()
            repo.set_api_key.return_value = True
            MockRepo.return_value = repo
            resp = app_client.delete("/account/api-key")
    finally:
        _clear(app_client)

    assert resp.status_code == 200
    repo.set_api_key.assert_called_once_with(1, None)


def test_get_api_key_returns_current(app_client):
    _override(app_client, _make_user(api_key="nxs_abc123"))
    try:
        resp = app_client.get("/account/api-key")
    finally:
        _clear(app_client)

    assert resp.status_code == 200
    assert resp.json() == {"api_key": "nxs_abc123", "has_api_key": True}


# ── /account/newsletter ─────────────────────────────────────────────────────
# /subscriptions/{email} GET/PATCH X-API-Key ister (paylaşımlı admin anahtarı),
# bu yüzden hesap sayfası kendi verisini SESSION'la okuyabilsin diye eklendi
# (v2.1.1, 18 Ağu 2026 — kullanıcı gerçek hesabında abonelik olmadığını fark
# edince, frontend'de bu özelliği açan hiçbir form olmadığı ortaya çıktı).

def test_newsletter_requires_auth(app_client):
    resp = app_client.get("/account/newsletter")
    assert resp.status_code == 401


def test_newsletter_not_subscribed(app_client):
    _override(app_client, _make_user())
    try:
        with patch("src.adapters.api.routers.account_router.SubscriberRepository") as MockRepo:
            repo = MagicMock()
            repo.get_by_email.return_value = None
            MockRepo.return_value = repo
            resp = app_client.get("/account/newsletter")
    finally:
        _clear(app_client)

    assert resp.status_code == 200
    assert resp.json() == {"subscribed": False}


def test_newsletter_returns_current_preferences(app_client):
    from src.domain.models.subscriber import Subscriber

    _override(app_client, _make_user())
    try:
        with patch("src.adapters.api.routers.account_router.SubscriberRepository") as MockRepo:
            repo = MagicMock()
            repo.get_by_email.return_value = Subscriber(
                email="me@test.com", keywords=["deprem"], preferred_sources=["TRT Haber"],
                preferred_topics=["Politics"], language="TR", frequency="daily", is_active=True,
            )
            MockRepo.return_value = repo
            resp = app_client.get("/account/newsletter")
    finally:
        _clear(app_client)

    assert resp.status_code == 200
    body = resp.json()
    assert body["subscribed"] is True
    assert body["frequency"] == "daily"
    assert body["keywords"] == ["deprem"]
    assert body["preferred_sources"] == ["TRT Haber"]
    assert body["preferred_topics"] == ["Politics"]


def test_newsletter_inactive_subscription_shown_as_not_subscribed(app_client):
    from src.domain.models.subscriber import Subscriber

    _override(app_client, _make_user())
    try:
        with patch("src.adapters.api.routers.account_router.SubscriberRepository") as MockRepo:
            repo = MagicMock()
            repo.get_by_email.return_value = Subscriber(email="me@test.com", is_active=False)
            MockRepo.return_value = repo
            resp = app_client.get("/account/newsletter")
    finally:
        _clear(app_client)

    assert resp.status_code == 200
    assert resp.json() == {"subscribed": False}
