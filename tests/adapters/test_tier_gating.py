"""v1.14 tier-gating: Pro/Kurumsal'ın vaat ettiği özelliklerin gerçekten
kilitli olduğunu doğrular — arama sonucu tavanı, ilişki grafı, WebSocket
canlı akış, anlık (instant) keyword alert.
"""

import pytest
from unittest.mock import MagicMock
from fastapi import HTTPException
from starlette.websockets import WebSocketDisconnect

from src.domain.models.user import User, UserTier, TIER_SEARCH_RESULT_CAP, tier_at_least
from src.adapters.api.auth_utils import check_tier_limit, get_optional_user
from src.dependencies import get_news_service, get_notifier
from src.adapters.api.routers.subscription_router import _get_repo, _get_user_repo


def _make_user(tier=UserTier.FREE, uid=1):
    return User(id=uid, email="u@test.com", password_hash="h", tier=tier)


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
