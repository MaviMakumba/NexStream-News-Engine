"""v1.14 tier-gating: Pro/Kurumsal'ın vaat ettiği özelliklerin gerçekten
kilitli olduğunu doğrular — arama sonucu tavanı, ilişki grafı, WebSocket
canlı akış, anlık (instant) keyword alert. v1.16'da ham veri export (Enterprise
özelliği) testleri de buraya eklendi.
"""

import pytest
from unittest.mock import MagicMock
from fastapi import HTTPException
from starlette.websockets import WebSocketDisconnect

from src.domain.models.user import User, UserTier, TIER_SEARCH_RESULT_CAP, tier_at_least
from src.domain.models.user import UserRole, role_at_least, effective_tier
from src.adapters.api.auth_utils import check_tier_limit, get_optional_user
from src.dependencies import get_news_service, get_notifier
from src.adapters.api.routers.subscription_router import _get_repo, _get_user_repo


def test_owner_role_ranks_above_admin():
    assert role_at_least(UserRole.OWNER, UserRole.ADMIN)
    assert not role_at_least(UserRole.ADMIN, UserRole.OWNER)


def test_effective_tier_owner_is_always_enterprise():
    assert effective_tier(UserTier.FREE, is_owner=True) == UserTier.ENTERPRISE


def test_effective_tier_non_owner_keeps_own_tier():
    assert effective_tier(UserTier.PRO, is_owner=False) == UserTier.PRO
    assert effective_tier(UserTier.FREE, is_owner=False) == UserTier.FREE


def _make_user(tier=UserTier.FREE, uid=1, role=UserRole.USER):
    return User(id=uid, email="u@test.com", password_hash="h", tier=tier, role=role)


# ── tier_at_least helper ────────────────────────────────────────────────────

def test_tier_at_least_free_not_pro():
    assert not tier_at_least(UserTier.FREE, UserTier.PRO)


def test_tier_at_least_pro_is_pro():
    assert tier_at_least(UserTier.PRO, UserTier.PRO)


def test_tier_at_least_enterprise_is_pro():
    assert tier_at_least(UserTier.ENTERPRISE, UserTier.PRO)


def test_tier_search_result_cap_values():
    assert TIER_SEARCH_RESULT_CAP[UserTier.FREE] == 10
    assert TIER_SEARCH_RESULT_CAP[UserTier.PRO] == 50
    assert TIER_SEARCH_RESULT_CAP[UserTier.ENTERPRISE] == 200


# ── /api/v1/news/search — sonuç sayısı tier'a göre tavanlanır ──────────────

def test_v1_search_clamps_free_tier_to_10(app_client):
    mock_service = MagicMock()
    mock_service.hybrid_search.return_value = []
    app_client.app.dependency_overrides[get_news_service] = lambda: mock_service
    app_client.app.dependency_overrides[check_tier_limit] = lambda: _make_user(UserTier.FREE)
    try:
        app_client.post("/api/v1/news/search", json={"query": "test", "n_results": 50})
    finally:
        app_client.app.dependency_overrides.pop(get_news_service, None)
        app_client.app.dependency_overrides.pop(check_tier_limit, None)
    called_n_results = mock_service.hybrid_search.call_args[0][1]
    assert called_n_results == 10


def test_v1_search_clamps_anonymous_to_free_cap(app_client):
    mock_service = MagicMock()
    mock_service.hybrid_search.return_value = []
    app_client.app.dependency_overrides[get_news_service] = lambda: mock_service
    app_client.app.dependency_overrides[check_tier_limit] = lambda: None
    try:
        app_client.post("/api/v1/news/search", json={"query": "test", "n_results": 200})
    finally:
        app_client.app.dependency_overrides.pop(get_news_service, None)
        app_client.app.dependency_overrides.pop(check_tier_limit, None)
    assert mock_service.hybrid_search.call_args[0][1] == 10


def test_v1_search_allows_pro_up_to_50(app_client):
    mock_service = MagicMock()
    mock_service.hybrid_search.return_value = []
    app_client.app.dependency_overrides[get_news_service] = lambda: mock_service
    app_client.app.dependency_overrides[check_tier_limit] = lambda: _make_user(UserTier.PRO)
    try:
        app_client.post("/api/v1/news/search", json={"query": "test", "n_results": 200})
    finally:
        app_client.app.dependency_overrides.pop(get_news_service, None)
        app_client.app.dependency_overrides.pop(check_tier_limit, None)
    assert mock_service.hybrid_search.call_args[0][1] == 50


def test_v1_search_allows_enterprise_up_to_200(app_client):
    mock_service = MagicMock()
    mock_service.hybrid_search.return_value = []
    app_client.app.dependency_overrides[get_news_service] = lambda: mock_service
    app_client.app.dependency_overrides[check_tier_limit] = lambda: _make_user(UserTier.ENTERPRISE)
    try:
        app_client.post("/api/v1/news/search", json={"query": "test", "n_results": 200})
    finally:
        app_client.app.dependency_overrides.pop(get_news_service, None)
        app_client.app.dependency_overrides.pop(check_tier_limit, None)
    assert mock_service.hybrid_search.call_args[0][1] == 200


def test_v1_search_allows_owner_up_to_200_despite_free_db_tier(app_client):
    mock_service = MagicMock()
    mock_service.hybrid_search.return_value = []
    app_client.app.dependency_overrides[get_news_service] = lambda: mock_service
    app_client.app.dependency_overrides[check_tier_limit] = lambda: _make_user(UserTier.FREE, role=UserRole.OWNER)
    try:
        app_client.post("/api/v1/news/search", json={"query": "test", "n_results": 200})
    finally:
        app_client.app.dependency_overrides.pop(get_news_service, None)
        app_client.app.dependency_overrides.pop(check_tier_limit, None)
    assert mock_service.hybrid_search.call_args[0][1] == 200


def test_v1_search_does_not_raise_requested_n_results(app_client):
    """Free bir kullanıcı 5 istiyorsa 10'a ZORLANMAMALI, sadece tavanlanmalı."""
    mock_service = MagicMock()
    mock_service.hybrid_search.return_value = []
    app_client.app.dependency_overrides[get_news_service] = lambda: mock_service
    app_client.app.dependency_overrides[check_tier_limit] = lambda: _make_user(UserTier.FREE)
    try:
        app_client.post("/api/v1/news/search", json={"query": "test", "n_results": 3})
    finally:
        app_client.app.dependency_overrides.pop(get_news_service, None)
        app_client.app.dependency_overrides.pop(check_tier_limit, None)
    assert mock_service.hybrid_search.call_args[0][1] == 3


def test_public_search_always_capped_to_free_regardless_of_request(app_client):
    """Anonim/public /news/search — kimlikten bağımsız her zaman Free tavanı."""
    mock_service = MagicMock()
    mock_service.hybrid_search.return_value = []
    app_client.app.dependency_overrides[get_news_service] = lambda: mock_service
    try:
        app_client.post("/news/search", json={"query": "test", "n_results": 200})
    finally:
        app_client.app.dependency_overrides.pop(get_news_service, None)
    assert mock_service.hybrid_search.call_args[0][1] == 10


def test_public_search_has_daily_quota_cap_registered():
    """v1.19: eski davranışta /news/search sadece 30/dk ile korunuyordu (~43k/gün
    IP-bazlı script kaçağı mümkündü). Artık bir günlük tavan da var. Gerçek
    HTTP döngüsüyle 200 isteği tüketmek yerine (slowapi'nin in-memory limiter
    state'i TÜM test session'ı boyunca paylaşılır — bkz. CLAUDE.md v1.17 notu)
    route'a kayıtlı limit tanımları doğrudan denetlenir."""
    from src.adapters.api.limiter import limiter
    import src.adapters.api.routers.news_router as news_router  # noqa: F401 — decorator side effect

    key = "src.adapters.api.routers.news_router.search_news"
    registered = {str(l.limit) for l in limiter._route_limits.get(key, [])}
    assert "30 per 1 minute" in registered
    assert "200 per 1 day" in registered


# ── /api/v1/news/{id}/related — Pro+ özelliği ───────────────────────────────

def test_v1_related_blocked_for_anonymous(app_client):
    app_client.app.dependency_overrides[check_tier_limit] = lambda: None
    try:
        resp = app_client.get("/api/v1/news/1/related")
    finally:
        app_client.app.dependency_overrides.pop(check_tier_limit, None)
    assert resp.status_code == 403


def test_v1_related_blocked_for_free_tier(app_client):
    app_client.app.dependency_overrides[check_tier_limit] = lambda: _make_user(UserTier.FREE)
    try:
        resp = app_client.get("/api/v1/news/1/related")
    finally:
        app_client.app.dependency_overrides.pop(check_tier_limit, None)
    assert resp.status_code == 403


def test_v1_related_allowed_for_pro(app_client):
    mock_service = MagicMock()
    mock_service.get_related.return_value = {"article_id": 1, "related": []}
    app_client.app.dependency_overrides[get_news_service] = lambda: mock_service
    app_client.app.dependency_overrides[check_tier_limit] = lambda: _make_user(UserTier.PRO)
    try:
        resp = app_client.get("/api/v1/news/1/related")
    finally:
        app_client.app.dependency_overrides.pop(get_news_service, None)
        app_client.app.dependency_overrides.pop(check_tier_limit, None)
    assert resp.status_code == 200


def test_v1_related_allowed_for_enterprise(app_client):
    mock_service = MagicMock()
    mock_service.get_related.return_value = {"article_id": 1, "related": []}
    app_client.app.dependency_overrides[get_news_service] = lambda: mock_service
    app_client.app.dependency_overrides[check_tier_limit] = lambda: _make_user(UserTier.ENTERPRISE)
    try:
        resp = app_client.get("/api/v1/news/1/related")
    finally:
        app_client.app.dependency_overrides.pop(get_news_service, None)
        app_client.app.dependency_overrides.pop(check_tier_limit, None)
    assert resp.status_code == 200


def test_v1_related_allowed_for_owner_despite_free_db_tier(app_client):
    mock_service = MagicMock()
    mock_service.get_related.return_value = {"article_id": 1, "related": []}
    app_client.app.dependency_overrides[get_news_service] = lambda: mock_service
    app_client.app.dependency_overrides[check_tier_limit] = lambda: _make_user(UserTier.FREE, role=UserRole.OWNER)
    try:
        resp = app_client.get("/api/v1/news/1/related")
    finally:
        app_client.app.dependency_overrides.pop(get_news_service, None)
        app_client.app.dependency_overrides.pop(check_tier_limit, None)
    assert resp.status_code == 200


def test_legacy_related_allowed_for_owner_despite_free_db_tier(app_client):
    mock_service = MagicMock()
    mock_service.get_related.return_value = {"article_id": 1, "related": []}
    app_client.app.dependency_overrides[get_news_service] = lambda: mock_service
    app_client.app.dependency_overrides[check_tier_limit] = lambda: _make_user(UserTier.FREE, role=UserRole.OWNER)
    try:
        resp = app_client.get("/news/1/related")
    finally:
        app_client.app.dependency_overrides.pop(get_news_service, None)
        app_client.app.dependency_overrides.pop(check_tier_limit, None)
    assert resp.status_code == 200


# ── /api/v1/news/export — Enterprise özelliği (v1.16) ───────────────────────

def _make_export_article():
    from src.domain.models.article import Article
    from datetime import datetime, timezone
    return Article(
        id=1, title="Test Haber", source="TRT Haber", url="https://trthaber.com/1",
        content="İçerik", summary="Özet", sentiment_label="Positive", sentiment_score=0.7,
        topic="Technology", entities={"persons": ["Ali"]},
        created_at=datetime(2026, 5, 26, tzinfo=timezone.utc),
    )


def test_v1_export_blocked_for_anonymous(app_client):
    app_client.app.dependency_overrides[check_tier_limit] = lambda: None
    try:
        resp = app_client.get("/api/v1/news/export")
    finally:
        app_client.app.dependency_overrides.pop(check_tier_limit, None)
    assert resp.status_code == 403


def test_v1_export_blocked_for_free_tier(app_client):
    app_client.app.dependency_overrides[check_tier_limit] = lambda: _make_user(UserTier.FREE)
    try:
        resp = app_client.get("/api/v1/news/export")
    finally:
        app_client.app.dependency_overrides.pop(check_tier_limit, None)
    assert resp.status_code == 403


def test_v1_export_blocked_for_pro_tier(app_client):
    """Export sadece Enterprise'a açık — pricing sayfasında bu şekilde vaat edildi, Pro+ değil."""
    app_client.app.dependency_overrides[check_tier_limit] = lambda: _make_user(UserTier.PRO)
    try:
        resp = app_client.get("/api/v1/news/export")
    finally:
        app_client.app.dependency_overrides.pop(check_tier_limit, None)
    assert resp.status_code == 403


def test_v1_export_allowed_for_enterprise_csv(app_client):
    mock_service = MagicMock()
    mock_service.export_articles.return_value = [_make_export_article()]
    app_client.app.dependency_overrides[get_news_service] = lambda: mock_service
    app_client.app.dependency_overrides[check_tier_limit] = lambda: _make_user(UserTier.ENTERPRISE)
    try:
        resp = app_client.get("/api/v1/news/export?format=csv")
    finally:
        app_client.app.dependency_overrides.pop(get_news_service, None)
        app_client.app.dependency_overrides.pop(check_tier_limit, None)
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/csv")
    assert "attachment" in resp.headers["content-disposition"]
    assert "Test Haber" in resp.text
    # entities CSV hücresine sığması için JSON string'e çevrilmeli (Python dict repr değil)
    assert "persons" in resp.text and "Ali" in resp.text
    assert "{'persons'" not in resp.text


def test_v1_export_allowed_for_enterprise_json(app_client):
    mock_service = MagicMock()
    mock_service.export_articles.return_value = [_make_export_article()]
    app_client.app.dependency_overrides[get_news_service] = lambda: mock_service
    app_client.app.dependency_overrides[check_tier_limit] = lambda: _make_user(UserTier.ENTERPRISE)
    try:
        resp = app_client.get("/api/v1/news/export?format=json")
    finally:
        app_client.app.dependency_overrides.pop(get_news_service, None)
        app_client.app.dependency_overrides.pop(check_tier_limit, None)
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("application/json")
    data = resp.json()
    assert len(data) == 1
    assert data[0]["title"] == "Test Haber"
    assert data[0]["entities"] == {"persons": ["Ali"]}


def test_v1_export_allowed_for_owner_despite_free_db_tier(app_client):
    mock_service = MagicMock()
    mock_service.export_articles.return_value = []
    app_client.app.dependency_overrides[get_news_service] = lambda: mock_service
    app_client.app.dependency_overrides[check_tier_limit] = lambda: _make_user(UserTier.FREE, role=UserRole.OWNER)
    try:
        resp = app_client.get("/api/v1/news/export")
    finally:
        app_client.app.dependency_overrides.pop(get_news_service, None)
        app_client.app.dependency_overrides.pop(check_tier_limit, None)
    assert resp.status_code == 200


def test_v1_export_invalid_format_returns_422(app_client):
    app_client.app.dependency_overrides[check_tier_limit] = lambda: _make_user(UserTier.ENTERPRISE)
    try:
        resp = app_client.get("/api/v1/news/export?format=xml")
    finally:
        app_client.app.dependency_overrides.pop(check_tier_limit, None)
    assert resp.status_code == 422


def test_v1_export_uses_configured_max_rows(app_client):
    from src.infrastructure.config.settings import settings
    mock_service = MagicMock()
    mock_service.export_articles.return_value = []
    app_client.app.dependency_overrides[get_news_service] = lambda: mock_service
    app_client.app.dependency_overrides[check_tier_limit] = lambda: _make_user(UserTier.ENTERPRISE)
    try:
        app_client.get("/api/v1/news/export")
    finally:
        app_client.app.dependency_overrides.pop(get_news_service, None)
        app_client.app.dependency_overrides.pop(check_tier_limit, None)
    assert mock_service.export_articles.call_args[0][0] == settings.export_max_rows


# ── /ws/feed — Pro+ özelliği ────────────────────────────────────────────────

def test_ws_feed_rejects_anonymous(app_client):
    # ÖNCE accept() SONRA close(1008) — handshake tamamlanır (gerçek tarayıcının
    # close code'u görebilmesi için gerekli, bkz. websocket_router.py yorumu),
    # yani `with websocket_connect(...)` bağlanır; ret ilk receive'de gelir.
    app_client.app.dependency_overrides[get_optional_user] = lambda: None
    app_client.app.dependency_overrides[get_notifier] = lambda: MagicMock()
    try:
        with app_client.websocket_connect("/ws/feed") as ws:
            with pytest.raises(WebSocketDisconnect) as exc_info:
                ws.receive_text()
        assert exc_info.value.code == 1008
    finally:
        app_client.app.dependency_overrides.pop(get_optional_user, None)
        app_client.app.dependency_overrides.pop(get_notifier, None)


def test_ws_feed_rejects_free_tier(app_client):
    app_client.app.dependency_overrides[get_optional_user] = lambda: _make_user(UserTier.FREE)
    app_client.app.dependency_overrides[get_notifier] = lambda: MagicMock()
    try:
        with app_client.websocket_connect("/ws/feed") as ws:
            with pytest.raises(WebSocketDisconnect) as exc_info:
                ws.receive_text()
        assert exc_info.value.code == 1008
    finally:
        app_client.app.dependency_overrides.pop(get_optional_user, None)
        app_client.app.dependency_overrides.pop(get_notifier, None)


def test_ws_feed_accepts_pro_tier(app_client):
    from src.adapters.notifications.websocket_notifier import WebSocketNotifier
    notifier = WebSocketNotifier()
    app_client.app.dependency_overrides[get_optional_user] = lambda: _make_user(UserTier.PRO)
    app_client.app.dependency_overrides[get_notifier] = lambda: notifier
    try:
        with app_client.websocket_connect("/ws/feed") as ws:
            assert notifier.connection_count == 1
    finally:
        app_client.app.dependency_overrides.pop(get_optional_user, None)
        app_client.app.dependency_overrides.pop(get_notifier, None)


def test_ws_feed_rejects_when_per_user_limit_reached(app_client):
    from src.adapters.notifications.websocket_notifier import WebSocketNotifier
    notifier = WebSocketNotifier(max_per_user=1, max_total=500)
    app_client.app.dependency_overrides[get_optional_user] = lambda: _make_user(UserTier.PRO, uid=7)
    app_client.app.dependency_overrides[get_notifier] = lambda: notifier
    try:
        with app_client.websocket_connect("/ws/feed"):
            assert notifier.connection_count == 1
            with app_client.websocket_connect("/ws/feed") as ws2:
                with pytest.raises(WebSocketDisconnect) as exc_info:
                    ws2.receive_text()
            assert exc_info.value.code == 1013
    finally:
        app_client.app.dependency_overrides.pop(get_optional_user, None)
        app_client.app.dependency_overrides.pop(get_notifier, None)


# ── /subscriptions — anlık (instant) uyarı Pro+ özelliği ────────────────────

def _mock_sub_repo():
    repo = MagicMock()
    from src.domain.models.subscriber import Subscriber
    repo.save_subscriber.return_value = Subscriber(
        id=1, email="test@example.com", keywords=[], frequency="instant", language="TR"
    )
    repo.update_subscriber.return_value = True
    return repo


def test_subscribe_instant_rejected_for_unregistered_email(app_client):
    mock_repo = _mock_sub_repo()
    mock_users = MagicMock()
    mock_users.get_by_email.return_value = None
    app_client.app.dependency_overrides[_get_repo] = lambda: mock_repo
    app_client.app.dependency_overrides[_get_user_repo] = lambda: mock_users
    try:
        r = app_client.post("/subscriptions/", json={"email": "anon@example.com", "frequency": "instant"})
    finally:
        app_client.app.dependency_overrides.pop(_get_repo, None)
        app_client.app.dependency_overrides.pop(_get_user_repo, None)
    assert r.status_code == 403


def test_subscribe_instant_rejected_for_free_tier_email(app_client):
    mock_repo = _mock_sub_repo()
    mock_users = MagicMock()
    mock_users.get_by_email.return_value = _make_user(UserTier.FREE)
    app_client.app.dependency_overrides[_get_repo] = lambda: mock_repo
    app_client.app.dependency_overrides[_get_user_repo] = lambda: mock_users
    try:
        r = app_client.post("/subscriptions/", json={"email": "free@example.com", "frequency": "instant"})
    finally:
        app_client.app.dependency_overrides.pop(_get_repo, None)
        app_client.app.dependency_overrides.pop(_get_user_repo, None)
    assert r.status_code == 403


def test_subscribe_instant_allowed_for_pro_tier_email(app_client):
    with_patch = None
    mock_repo = _mock_sub_repo()
    mock_users = MagicMock()
    mock_users.get_by_email.return_value = _make_user(UserTier.PRO)
    app_client.app.dependency_overrides[_get_repo] = lambda: mock_repo
    app_client.app.dependency_overrides[_get_user_repo] = lambda: mock_users
    try:
        from unittest.mock import patch
        with patch("src.adapters.api.routers.subscription_router.get_email_adapter") as mock_email:
            mock_email.return_value.send_welcome.return_value = True
            r = app_client.post("/subscriptions/", json={"email": "pro@example.com", "frequency": "instant"})
    finally:
        app_client.app.dependency_overrides.pop(_get_repo, None)
        app_client.app.dependency_overrides.pop(_get_user_repo, None)
    assert r.status_code == 201


def test_subscribe_daily_allowed_without_any_user_account(app_client):
    """daily/never her zaman serbest — sadece instant Pro gerektirir."""
    mock_repo = _mock_sub_repo()
    mock_users = MagicMock()
    mock_users.get_by_email.return_value = None
    app_client.app.dependency_overrides[_get_repo] = lambda: mock_repo
    app_client.app.dependency_overrides[_get_user_repo] = lambda: mock_users
    try:
        from unittest.mock import patch
        with patch("src.adapters.api.routers.subscription_router.get_email_adapter") as mock_email:
            mock_email.return_value.send_welcome.return_value = True
            r = app_client.post("/subscriptions/", json={"email": "anyone@example.com", "frequency": "daily"})
    finally:
        app_client.app.dependency_overrides.pop(_get_repo, None)
        app_client.app.dependency_overrides.pop(_get_user_repo, None)
    assert r.status_code == 201
    mock_users.get_by_email.assert_not_called()


def test_update_preferences_instant_rejected_for_free_tier(app_client):
    from src.domain.models.subscriber import Subscriber
    mock_repo = MagicMock()
    mock_repo.get_by_email.return_value = Subscriber(
        id=1, email="free@example.com", keywords=[], frequency="daily", language="TR", is_active=True
    )
    mock_users = MagicMock()
    mock_users.get_by_email.return_value = _make_user(UserTier.FREE)
    app_client.app.dependency_overrides[_get_repo] = lambda: mock_repo
    app_client.app.dependency_overrides[_get_user_repo] = lambda: mock_users
    from src.adapters.api.auth import verify_api_key
    app_client.app.dependency_overrides[verify_api_key] = lambda: None
    try:
        r = app_client.patch("/subscriptions/free@example.com", json={"frequency": "instant"})
    finally:
        app_client.app.dependency_overrides.pop(_get_repo, None)
        app_client.app.dependency_overrides.pop(_get_user_repo, None)
        app_client.app.dependency_overrides.pop(verify_api_key, None)
    assert r.status_code == 403
