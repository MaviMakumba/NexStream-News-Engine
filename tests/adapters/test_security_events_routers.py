"""Güvenlik günlüğü olaylarının router'lardan yazıldığını doğrular (13 Eylül 2026).

Her test `record_security_event`'i ilgili router modülünde mock'lar ve doğru
category/event_type/email/user_id/detail ile çağrıldığını kontrol eder. IP/UA/
request_id doldurma zaten test_security_audit.py'de doğrulanıyor.
"""

from unittest.mock import MagicMock, patch, ANY

from src.adapters.api.auth_utils import get_current_user, get_optional_user
from src.domain.models.security_event import EventCategory, EventType
from src.domain.models.user import User, UserRole, UserSession, UserTier
from src.infrastructure.config.database import get_db
from src.infrastructure.config.settings import settings
from datetime import datetime, timedelta, timezone

API_KEY = {"X-API-Key": settings.api_key}


def _user(id=1, email="test@example.com", role=UserRole.USER, verified=True):
    return User(id=id, email=email, password_hash="h", tier=UserTier.FREE, role=role, email_verified=verified)


def _session(user_id=1):
    return UserSession(user_id=user_id, token="tok", expires_at=datetime.now(timezone.utc) + timedelta(days=1))


def _override_user(app_client, user):
    app_client.app.dependency_overrides[get_current_user] = lambda: user
    app_client.app.dependency_overrides[get_optional_user] = lambda: user
    app_client.app.dependency_overrides[get_db] = lambda: MagicMock()


def _clear(app_client):
    app_client.app.dependency_overrides.clear()


def _kwargs(mock):
    return mock.call_args.kwargs


# ── auth ──────────────────────────────────────────────────────────────────────

def test_login_failure_records_attempted_email_even_when_user_unknown(app_client):
    with patch("src.adapters.api.routers.auth_router.UserRepository") as MockRepo, \
         patch("src.adapters.api.routers.auth_router.record_security_event") as rec:
        MockRepo.return_value.get_by_email.return_value = None
        r = app_client.post("/auth/login", json={"email": "victim@example.com", "password": "x"})
    assert r.status_code == 401
    rec.assert_called_once_with(ANY, ANY, EventCategory.AUTH, EventType.LOGIN_FAILURE,
                                email="victim@example.com", user_id=None, detail=ANY)


def test_login_success_records_user_id(app_client):
    with patch("src.adapters.api.routers.auth_router.UserRepository") as MockRepo, \
         patch("src.adapters.api.routers.auth_router._verify_password", return_value=True), \
         patch("src.adapters.api.routers.auth_router.record_security_event") as rec:
        MockRepo.return_value.get_by_email.return_value = _user(id=7)
        MockRepo.return_value.create_session.return_value = _session(7)
        r = app_client.post("/auth/login", json={"email": "test@example.com", "password": "ok"})
    assert r.status_code == 200
    assert _kwargs(rec)["user_id"] == 7
    assert rec.call_args.args[2:] == (EventCategory.AUTH, EventType.LOGIN_SUCCESS)


def test_register_records_event(app_client):
    with patch("src.adapters.api.routers.auth_router.UserRepository") as MockRepo, \
         patch("src.adapters.api.routers.auth_router._assert_deliverable_email"), \
         patch("src.adapters.api.routers.auth_router.get_email_adapter"), \
         patch("src.adapters.api.routers.auth_router.record_security_event") as rec:
        MockRepo.return_value.get_by_email.return_value = None
        MockRepo.return_value.create_user.return_value = _user(id=16, email="new@example.com")
        MockRepo.return_value.create_session.return_value = _session(16)
        r = app_client.post("/auth/register", json={"email": "new@example.com", "password": "secret123"})
    assert r.status_code == 201
    assert rec.call_args.args[2:] == (EventCategory.AUTH, EventType.REGISTER)
    assert _kwargs(rec)["user_id"] == 16 and _kwargs(rec)["email"] == "new@example.com"


def test_forgot_password_records_request_regardless_of_account_existence(app_client):
    with patch("src.adapters.api.routers.auth_router.UserRepository") as MockRepo, \
         patch("src.adapters.api.routers.auth_router.record_security_event") as rec:
        MockRepo.return_value.get_by_email.return_value = None
        app_client.post("/auth/forgot-password", json={"email": "ghost@example.com"})
    assert rec.call_args.args[2:] == (EventCategory.AUTH, EventType.PASSWORD_RESET_REQUESTED)
    assert _kwargs(rec)["email"] == "ghost@example.com"


# ── admin ─────────────────────────────────────────────────────────────────────

def test_role_change_records_actor_and_target(app_client):
    admin = _user(id=1, email="admin@example.com", role=UserRole.ADMIN)
    _override_user(app_client, admin)
    try:
        with patch("src.adapters.api.routers.admin_router.UserRepository") as MockRepo, \
             patch("src.adapters.api.routers.admin_router.record_security_event") as rec:
            MockRepo.return_value.get_by_id.return_value = _user(id=5, email="target@example.com")
            MockRepo.return_value.update_role.return_value = True
            r = app_client.patch("/admin/users/5/role", json={"role": "moderator"})
    finally:
        _clear(app_client)
    assert r.status_code == 200
    assert rec.call_args.args[2:] == (EventCategory.ADMIN, EventType.ROLE_CHANGED)
    kw = _kwargs(rec)
    assert kw["email"] == "target@example.com" and kw["user_id"] == 5
    assert "moderator" in kw["detail"] and "admin@example.com" in kw["detail"]


def test_ban_records_event(app_client):
    admin = _user(id=1, email="admin@example.com", role=UserRole.ADMIN)
    _override_user(app_client, admin)
    try:
        with patch("src.adapters.api.routers.admin_router.UserRepository") as MockRepo, \
             patch("src.adapters.api.routers.admin_router.record_security_event") as rec:
            MockRepo.return_value.get_by_id.return_value = _user(id=5, email="target@example.com")
            MockRepo.return_value.set_active.return_value = True
            r = app_client.patch("/admin/users/5/active", json={"is_active": False})
    finally:
        _clear(app_client)
    assert r.status_code == 200
    assert rec.call_args.args[2:] == (EventCategory.ADMIN, EventType.USER_BANNED)


def test_admin_access_denied_is_recorded(app_client):
    with patch("src.main.record_security_event") as rec:
        r = app_client.get("/admin/users")
    assert r.status_code == 401
    assert rec.call_args.args[2:] == (EventCategory.ACCESS, EventType.ADMIN_ACCESS_DENIED)
    assert "401" in _kwargs(rec)["detail"]


def test_non_admin_401_is_not_recorded_as_admin_denial(app_client):
    with patch("src.main.record_security_event") as rec:
        app_client.get("/account/usage")
    rec.assert_not_called()


# ── access: API anahtarı ──────────────────────────────────────────────────────

def test_api_key_generation_and_revocation_recorded(app_client):
    _override_user(app_client, _user(id=3))
    try:
        with patch("src.adapters.api.routers.account_router.UserRepository"), \
             patch("src.adapters.api.routers.account_router.record_security_event") as rec:
            app_client.post("/account/api-key")
            app_client.delete("/account/api-key")
    finally:
        _clear(app_client)
    types = [c.args[3] for c in rec.call_args_list]
    assert types == [EventType.API_KEY_GENERATED, EventType.API_KEY_REVOKED]
    assert all(c.args[2] == EventCategory.ACCESS for c in rec.call_args_list)


# ── abuse: rate limit ─────────────────────────────────────────────────────────

def test_rate_limit_hit_is_recorded(app_client):
    with patch("src.adapters.api.routers.auth_router.UserRepository") as MockRepo, \
         patch("src.main.record_security_event") as rec:
        MockRepo.return_value.get_by_email.return_value = None
        statuses = [app_client.post("/auth/login", json={"email": "v@example.com", "password": "x"}).status_code
                    for _ in range(16)]
    assert statuses[-1] == 429
    assert rec.call_args.args[2:] == (EventCategory.ABUSE, EventType.RATE_LIMITED)
    assert "/auth/login" in _kwargs(rec)["detail"]


# ── admin okuma ucu ───────────────────────────────────────────────────────────

def test_security_events_endpoint_requires_moderator(app_client):
    assert app_client.get("/admin/security-events").status_code == 401


def test_security_events_endpoint_filters_and_serializes(app_client):
    from src.domain.models.security_event import SecurityEvent
    app_client.app.dependency_overrides[get_db] = lambda: MagicMock()
    try:
        with patch("src.adapters.api.routers.admin_router.SecurityEventRepository") as MockRepo:
            MockRepo.return_value.query.return_value = [SecurityEvent(
                id=1, category="auth", event_type="login_failure", email="a@x.com", ip="1.2.3.4",
                user_agent="UA", request_id="rid", path="/auth/login", detail=None,
                created_at=datetime(2026, 9, 12, 11, 22, tzinfo=timezone.utc),
            )]
            r = app_client.get("/admin/security-events?email=a@x.com&ip=1.2.3.4&event_type=login_failure&hours=24&limit=50",
                               headers=API_KEY)
    finally:
        _clear(app_client)
    assert r.status_code == 200
    kw = MockRepo.return_value.query.call_args.kwargs
    assert kw["email"] == "a@x.com" and kw["ip"] == "1.2.3.4" and kw["event_type"] == "login_failure" and kw["limit"] == 50
    assert (datetime.now(timezone.utc) - kw["since"]).total_seconds() < 24 * 3600 + 60
    item = r.json()[0]
    assert item["event_type"] == "login_failure" and item["ip"] == "1.2.3.4" and item["request_id"] == "rid"
