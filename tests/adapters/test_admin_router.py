import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock
from src.infrastructure.config.database import get_db
from src.adapters.api.auth_utils import get_optional_user
from src.domain.models.user import User, UserTier, UserRole


_API_KEY = "dev-key-change-me"
_HEADERS = {"x-api-key": _API_KEY}


def _make_user(id=1, email="user@test.com", tier=UserTier.FREE, stripe_customer_id=None,
               is_admin=False, role=None):
    """`is_admin=True` eski testlerle uyum için `role=admin`'e eşlenir."""
    if role is None:
        role = UserRole.ADMIN if is_admin else UserRole.USER
    return User(
        id=id, email=email, password_hash="x", name="Test User", tier=tier,
        is_active=True, role=role, stripe_customer_id=stripe_customer_id,
        created_at=datetime.now(timezone.utc),
    )


def _make_mock_db():
    db = MagicMock()
    db.close = MagicMock()
    return db


def _sponsor_dict(id=1, name="Acme Corp", is_active=True):
    return {
        "id": id,
        "name": name,
        "url": "https://acme.example.com",
        "message": "Best product ever",
        "active_from": datetime.now(timezone.utc).isoformat(),
        "active_until": (datetime.now(timezone.utc) + timedelta(days=30)).isoformat(),
        "is_active": is_active,
    }


def _sponsor_orm(id=1, name="Acme Corp", is_active=True):
    m = MagicMock()
    m.id = id
    m.name = name
    m.url = "https://acme.example.com"
    m.message = "Best product ever"
    m.active_from = datetime.now(timezone.utc)
    m.active_until = datetime.now(timezone.utc) + timedelta(days=30)
    m.is_active = is_active
    return m


# ── Usage stats ───────────────────────────────────────────────────────────────

def test_get_usage_stats_requires_api_key(app_client):
    resp = app_client.get("/admin/usage")
    assert resp.status_code == 401


def test_get_usage_stats_returns_list(app_client):
    db = _make_mock_db()
    app_client.app.dependency_overrides[get_db] = lambda: db
    try:
        with patch("src.adapters.api.routers.admin_router.UserRepository") as MockRepo:
            repo = MagicMock()
            repo.get_usage_stats.return_value = [
                {"user_id": 1, "endpoint": "/api/v1/news", "count": 42, "avg_ms": 120.5}
            ]
            MockRepo.return_value = repo
            resp = app_client.get("/admin/usage", headers=_HEADERS)
    finally:
        app_client.app.dependency_overrides.pop(get_db, None)

    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert data[0]["count"] == 42


def test_get_usage_stats_with_user_id_filter(app_client):
    db = _make_mock_db()
    app_client.app.dependency_overrides[get_db] = lambda: db
    try:
        with patch("src.adapters.api.routers.admin_router.UserRepository") as MockRepo:
            repo = MagicMock()
            repo.get_usage_stats.return_value = []
            MockRepo.return_value = repo
            resp = app_client.get("/admin/usage?user_id=5&days=7", headers=_HEADERS)
    finally:
        app_client.app.dependency_overrides.pop(get_db, None)

    assert resp.status_code == 200
    repo.get_usage_stats.assert_called_once_with(user_id=5, days=7)


# ── Kullanıcı listesi ─────────────────────────────────────────────────────────

def test_list_users_requires_api_key(app_client):
    resp = app_client.get("/admin/users")
    assert resp.status_code == 401


def test_list_users_returns_items_with_is_paying(app_client):
    db = _make_mock_db()
    app_client.app.dependency_overrides[get_db] = lambda: db
    try:
        with patch("src.adapters.api.routers.admin_router.UserRepository") as MockRepo:
            repo = MagicMock()
            repo.list_users.return_value = [
                _make_user(id=1, email="paying@test.com", tier=UserTier.PRO, stripe_customer_id="cus_123"),
                _make_user(id=2, email="devmode@test.com", tier=UserTier.ENTERPRISE, stripe_customer_id=None),
            ]
            repo.count_users.return_value = 2
            MockRepo.return_value = repo
            resp = app_client.get("/admin/users", headers=_HEADERS)
    finally:
        app_client.app.dependency_overrides.pop(get_db, None)

    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 2
    assert data["items"][0]["email"] == "paying@test.com"
    assert data["items"][0]["tier"] == "pro"
    assert data["items"][0]["role"] == "user"
    assert data["items"][0]["is_paying"] is True
    assert data["items"][1]["is_paying"] is False


def test_list_users_passes_pagination_and_tier_filter(app_client):
    db = _make_mock_db()
    app_client.app.dependency_overrides[get_db] = lambda: db
    try:
        with patch("src.adapters.api.routers.admin_router.UserRepository") as MockRepo:
            repo = MagicMock()
            repo.list_users.return_value = []
            repo.count_users.return_value = 0
            MockRepo.return_value = repo
            resp = app_client.get("/admin/users?limit=10&offset=20&tier=pro", headers=_HEADERS)
    finally:
        app_client.app.dependency_overrides.pop(get_db, None)

    assert resp.status_code == 200
    repo.list_users.assert_called_once_with(limit=10, offset=20, tier="pro")
    repo.count_users.assert_called_once_with(tier="pro")


# ── Rol değiştirme ────────────────────────────────────────────────────────────

def test_update_user_role_requires_admin_not_just_moderator(app_client):
    moderator = _make_user(id=1, role=UserRole.MODERATOR)
    app_client.app.dependency_overrides[get_optional_user] = lambda: moderator
    try:
        resp = app_client.patch("/admin/users/2/role", json={"role": "moderator"})
    finally:
        app_client.app.dependency_overrides.pop(get_optional_user, None)

    assert resp.status_code == 403


def test_update_user_role_success(app_client):
    admin = _make_user(id=1, role=UserRole.ADMIN)
    db = _make_mock_db()
    app_client.app.dependency_overrides[get_optional_user] = lambda: admin
    app_client.app.dependency_overrides[get_db] = lambda: db
    try:
        with patch("src.adapters.api.routers.admin_router.UserRepository") as MockRepo:
            repo = MagicMock()
            repo.update_role.return_value = True
            MockRepo.return_value = repo
            resp = app_client.patch("/admin/users/2/role", json={"role": "moderator"})
    finally:
        app_client.app.dependency_overrides.pop(get_optional_user, None)
        app_client.app.dependency_overrides.pop(get_db, None)

    assert resp.status_code == 200
    assert resp.json() == {"id": 2, "role": "moderator"}
    repo.update_role.assert_called_once_with(2, "moderator")


def test_update_user_role_rejects_invalid_role(app_client):
    admin = _make_user(id=1, role=UserRole.ADMIN)
    app_client.app.dependency_overrides[get_optional_user] = lambda: admin
    try:
        resp = app_client.patch("/admin/users/2/role", json={"role": "superuser"})
    finally:
        app_client.app.dependency_overrides.pop(get_optional_user, None)

    assert resp.status_code == 400


def test_update_user_role_rejects_self_demotion(app_client):
    """Admin kendi rolünü admin'den başka bir şeye düşüremez (kilitlenmeyi önler)."""
    admin = _make_user(id=1, role=UserRole.ADMIN)
    app_client.app.dependency_overrides[get_optional_user] = lambda: admin
    try:
        resp = app_client.patch("/admin/users/1/role", json={"role": "user"})
    finally:
        app_client.app.dependency_overrides.pop(get_optional_user, None)

    assert resp.status_code == 400


def test_update_user_role_404_for_missing_user(app_client):
    admin = _make_user(id=1, role=UserRole.ADMIN)
    db = _make_mock_db()
    app_client.app.dependency_overrides[get_optional_user] = lambda: admin
    app_client.app.dependency_overrides[get_db] = lambda: db
    try:
        with patch("src.adapters.api.routers.admin_router.UserRepository") as MockRepo:
            repo = MagicMock()
            repo.update_role.return_value = False
            MockRepo.return_value = repo
            resp = app_client.patch("/admin/users/999/role", json={"role": "admin"})
    finally:
        app_client.app.dependency_overrides.pop(get_optional_user, None)
        app_client.app.dependency_overrides.pop(get_db, None)

    assert resp.status_code == 404


# ── Sponsors ──────────────────────────────────────────────────────────────────

def test_list_sponsors_requires_api_key(app_client):
    resp = app_client.get("/admin/sponsors")
    assert resp.status_code == 401


def test_list_sponsors_returns_list(app_client):
    db = _make_mock_db()
    orm = _sponsor_orm()
    db.query.return_value.order_by.return_value.all.return_value = [orm]
    app_client.app.dependency_overrides[get_db] = lambda: db
    try:
        resp = app_client.get("/admin/sponsors", headers=_HEADERS)
    finally:
        app_client.app.dependency_overrides.pop(get_db, None)

    assert resp.status_code == 200
    assert isinstance(resp.json(), list)
    assert resp.json()[0]["name"] == "Acme Corp"


def test_create_sponsor(app_client):
    db = _make_mock_db()
    app_client.app.dependency_overrides[get_db] = lambda: db
    payload = {
        "name": "Acme Corp",
        "url": "https://acme.example.com",
        "message": "Try Acme today!",
        "active_from": datetime.now(timezone.utc).isoformat(),
        "active_until": (datetime.now(timezone.utc) + timedelta(days=30)).isoformat(),
    }
    try:
        resp = app_client.post("/admin/sponsors", json=payload, headers=_HEADERS)
    finally:
        app_client.app.dependency_overrides.pop(get_db, None)

    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Acme Corp"
    assert data["url"] == "https://acme.example.com"
    assert data["is_active"] is True
    db.add.assert_called_once()
    db.commit.assert_called_once()


def test_deactivate_sponsor(app_client):
    db = _make_mock_db()
    orm = _sponsor_orm()
    db.get.return_value = orm
    app_client.app.dependency_overrides[get_db] = lambda: db
    try:
        resp = app_client.delete("/admin/sponsors/1", headers=_HEADERS)
    finally:
        app_client.app.dependency_overrides.pop(get_db, None)

    assert resp.status_code == 200
    assert resp.json()["is_active"] is False


def test_deactivate_nonexistent_sponsor_returns_404(app_client):
    db = _make_mock_db()
    db.get.return_value = None
    app_client.app.dependency_overrides[get_db] = lambda: db
    try:
        resp = app_client.delete("/admin/sponsors/999", headers=_HEADERS)
    finally:
        app_client.app.dependency_overrides.pop(get_db, None)

    assert resp.status_code == 404
