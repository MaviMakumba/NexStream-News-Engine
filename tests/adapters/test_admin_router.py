import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock
from src.infrastructure.config.database import get_db
from src.infrastructure.config.settings import settings
from src.adapters.api.auth_utils import get_optional_user
from src.domain.models.user import User, UserTier, UserRole


# Gerçek .env'deki API_KEY ne olursa olsun (güvenlik denetiminden sonra artık
# "dev-key-change-me" değil, rastgele üretilmiş bir değer) settings ile aynı
# değeri kullanır — hardcoded bir string, .env'in o anki içeriğine bağımlı olurdu.
_API_KEY = settings.api_key
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


def test_list_users_returns_email_verified_flag(app_client):
    """Admin tablosu 'Aktif/Pasif'ten bağımsız bir e-posta doğrulama sütunu
    gösterecek (18 Ağu 2026 tartışması) — is_active ile karıştırılmamalı,
    ayrı bir alan olarak dönmeli."""
    db = _make_mock_db()
    app_client.app.dependency_overrides[get_db] = lambda: db
    try:
        with patch("src.adapters.api.routers.admin_router.UserRepository") as MockRepo:
            repo = MagicMock()
            verified_user = _make_user(id=1, email="verified@test.com")
            verified_user.email_verified = True
            unverified_user = _make_user(id=2, email="unverified@test.com")
            unverified_user.email_verified = False
            repo.list_users.return_value = [verified_user, unverified_user]
            repo.count_users.return_value = 2
            MockRepo.return_value = repo
            resp = app_client.get("/admin/users", headers=_HEADERS)
    finally:
        app_client.app.dependency_overrides.pop(get_db, None)

    assert resp.status_code == 200
    data = resp.json()
    assert data["items"][0]["email_verified"] is True
    assert data["items"][1]["email_verified"] is False


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

def test_update_user_role_rejects_plain_user_actor(app_client):
    """Router-level require_moderator giriş kapısı: plain user rol değiştiremez.

    Kademeli rol yönetiminde (v2.1) asıl yetki sınırlaması handler içindeki
    rank-comparison'dadır (bkz. matris testleri), ama moderator-altı hiç
    handler'a giremez — bunu doğrular.
    """
    plain_user = _make_user(id=1, role=UserRole.USER)
    app_client.app.dependency_overrides[get_optional_user] = lambda: plain_user
    try:
        resp = app_client.patch("/admin/users/2/role", json={"role": "user"})
    finally:
        app_client.app.dependency_overrides.pop(get_optional_user, None)

    assert resp.status_code == 403


def test_update_user_role_success(app_client):
    admin = _make_user(id=1, role=UserRole.ADMIN)
    target = _make_user(id=2, role=UserRole.USER)
    db = _make_mock_db()
    app_client.app.dependency_overrides[get_optional_user] = lambda: admin
    app_client.app.dependency_overrides[get_db] = lambda: db
    try:
        with patch("src.adapters.api.routers.admin_router.UserRepository") as MockRepo:
            repo = MagicMock()
            repo.get_by_id.return_value = target
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


def test_update_user_role_rejects_self_change(app_client):
    """Kimse kendi rolünü kendisi değiştiremez (kilitlenmeyi önler)."""
    admin = _make_user(id=1, role=UserRole.ADMIN)
    app_client.app.dependency_overrides[get_optional_user] = lambda: admin
    try:
        resp = app_client.patch("/admin/users/1/role", json={"role": "moderator"})
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
            repo.get_by_id.return_value = None
            MockRepo.return_value = repo
            resp = app_client.patch("/admin/users/999/role", json={"role": "admin"})
    finally:
        app_client.app.dependency_overrides.pop(get_optional_user, None)
        app_client.app.dependency_overrides.pop(get_db, None)

    assert resp.status_code == 404


def _target(id, role):
    return _make_user(id=id, role=role)


def test_moderator_can_promote_plain_user_to_moderator(app_client):
    moderator = _make_user(id=1, role=UserRole.MODERATOR)
    db = _make_mock_db()
    app_client.app.dependency_overrides[get_optional_user] = lambda: moderator
    app_client.app.dependency_overrides[get_db] = lambda: db
    try:
        with patch("src.adapters.api.routers.admin_router.UserRepository") as MockRepo:
            repo = MagicMock()
            repo.get_by_id.return_value = _target(2, UserRole.USER)
            repo.update_role.return_value = True
            MockRepo.return_value = repo
            resp = app_client.patch("/admin/users/2/role", json={"role": "moderator"})
    finally:
        app_client.app.dependency_overrides.pop(get_optional_user, None)
        app_client.app.dependency_overrides.pop(get_db, None)
    assert resp.status_code == 200


def test_moderator_cannot_touch_another_moderator(app_client):
    moderator = _make_user(id=1, role=UserRole.MODERATOR)
    db = _make_mock_db()
    app_client.app.dependency_overrides[get_optional_user] = lambda: moderator
    app_client.app.dependency_overrides[get_db] = lambda: db
    try:
        with patch("src.adapters.api.routers.admin_router.UserRepository") as MockRepo:
            repo = MagicMock()
            repo.get_by_id.return_value = _target(2, UserRole.MODERATOR)
            MockRepo.return_value = repo
            resp = app_client.patch("/admin/users/2/role", json={"role": "user"})
    finally:
        app_client.app.dependency_overrides.pop(get_optional_user, None)
        app_client.app.dependency_overrides.pop(get_db, None)
    assert resp.status_code == 403


def test_admin_can_promote_moderator_to_admin(app_client):
    admin = _make_user(id=1, role=UserRole.ADMIN)
    db = _make_mock_db()
    app_client.app.dependency_overrides[get_optional_user] = lambda: admin
    app_client.app.dependency_overrides[get_db] = lambda: db
    try:
        with patch("src.adapters.api.routers.admin_router.UserRepository") as MockRepo:
            repo = MagicMock()
            repo.get_by_id.return_value = _target(2, UserRole.MODERATOR)
            repo.update_role.return_value = True
            MockRepo.return_value = repo
            resp = app_client.patch("/admin/users/2/role", json={"role": "admin"})
    finally:
        app_client.app.dependency_overrides.pop(get_optional_user, None)
        app_client.app.dependency_overrides.pop(get_db, None)
    assert resp.status_code == 200


def test_admin_cannot_touch_another_admin(app_client):
    admin = _make_user(id=1, role=UserRole.ADMIN)
    db = _make_mock_db()
    app_client.app.dependency_overrides[get_optional_user] = lambda: admin
    app_client.app.dependency_overrides[get_db] = lambda: db
    try:
        with patch("src.adapters.api.routers.admin_router.UserRepository") as MockRepo:
            repo = MagicMock()
            repo.get_by_id.return_value = _target(2, UserRole.ADMIN)
            MockRepo.return_value = repo
            resp = app_client.patch("/admin/users/2/role", json={"role": "user"})
    finally:
        app_client.app.dependency_overrides.pop(get_optional_user, None)
        app_client.app.dependency_overrides.pop(get_db, None)
    assert resp.status_code == 403


def test_owner_can_demote_an_admin(app_client):
    owner = _make_user(id=1, role=UserRole.OWNER)
    db = _make_mock_db()
    app_client.app.dependency_overrides[get_optional_user] = lambda: owner
    app_client.app.dependency_overrides[get_db] = lambda: db
    try:
        with patch("src.adapters.api.routers.admin_router.UserRepository") as MockRepo:
            repo = MagicMock()
            repo.get_by_id.return_value = _target(2, UserRole.ADMIN)
            repo.update_role.return_value = True
            MockRepo.return_value = repo
            resp = app_client.patch("/admin/users/2/role", json={"role": "user"})
    finally:
        app_client.app.dependency_overrides.pop(get_optional_user, None)
        app_client.app.dependency_overrides.pop(get_db, None)
    assert resp.status_code == 200


def test_moderator_cannot_assign_admin_role(app_client):
    """Kural 4 (atanacak rol actor'un rolünü aşamaz) — kural 3'ten AYRI ve
    onun yakalayamadığı bir eskalasyon vektörünü kapatır: hedefin rolü
    (user, rank 0) actor'dan (moderator, rank 1) kesinlikle düşük olduğu için
    kural 3 tek başına bu isteğe izin verirdi; sadece kural 4 (moderator
    admin, rank 2, atayamaz) bunu engeller."""
    moderator = _make_user(id=1, role=UserRole.MODERATOR)
    db = _make_mock_db()
    app_client.app.dependency_overrides[get_optional_user] = lambda: moderator
    app_client.app.dependency_overrides[get_db] = lambda: db
    try:
        with patch("src.adapters.api.routers.admin_router.UserRepository") as MockRepo:
            repo = MagicMock()
            repo.get_by_id.return_value = _target(2, UserRole.USER)
            MockRepo.return_value = repo
            resp = app_client.patch("/admin/users/2/role", json={"role": "admin"})
    finally:
        app_client.app.dependency_overrides.pop(get_optional_user, None)
        app_client.app.dependency_overrides.pop(get_db, None)
    assert resp.status_code == 403
    repo.update_role.assert_not_called()


def test_owner_actor_cannot_change_own_role(app_client):
    """Kendi rolünü değiştirememe guard'ı role'den bağımsız — owner actor için
    de doğrulanmalı (kod ortak ama daha önce sadece admin actor'la test edilmişti)."""
    owner = _make_user(id=1, role=UserRole.OWNER)
    app_client.app.dependency_overrides[get_optional_user] = lambda: owner
    try:
        resp = app_client.patch("/admin/users/1/role", json={"role": "admin"})
    finally:
        app_client.app.dependency_overrides.pop(get_optional_user, None)
    assert resp.status_code == 400


def test_owner_role_can_never_be_assigned(app_client):
    admin = _make_user(id=1, role=UserRole.ADMIN)
    app_client.app.dependency_overrides[get_optional_user] = lambda: admin
    try:
        resp = app_client.patch("/admin/users/2/role", json={"role": "owner"})
    finally:
        app_client.app.dependency_overrides.pop(get_optional_user, None)
    assert resp.status_code == 400


# ── Kullanıcı banlama / aktifleştirme (v2.2) ────────────────────────────────
# `role` endpoint'iyle AYNI kademeli yetki deseni — router-level require_moderator
# giriş kapısı, handler içinde rank-comparison. Ban ayrıca banlanan kullanıcının
# aktif oturumlarını da düşürür (çalınmış/hâlâ açık bir oturumla erişime devam
# edemesin diye) — hesap silmedeki "irreversible eylem" ilkesiyle aynı gerekçe.

def test_update_user_active_rejects_plain_user_actor(app_client):
    plain_user = _make_user(id=1, role=UserRole.USER)
    app_client.app.dependency_overrides[get_optional_user] = lambda: plain_user
    try:
        resp = app_client.patch("/admin/users/2/active", json={"is_active": False})
    finally:
        app_client.app.dependency_overrides.pop(get_optional_user, None)
    assert resp.status_code == 403


def test_update_user_active_ban_success_kills_sessions(app_client):
    admin = _make_user(id=1, role=UserRole.ADMIN)
    db = _make_mock_db()
    app_client.app.dependency_overrides[get_optional_user] = lambda: admin
    app_client.app.dependency_overrides[get_db] = lambda: db
    try:
        with patch("src.adapters.api.routers.admin_router.UserRepository") as MockRepo:
            repo = MagicMock()
            repo.get_by_id.return_value = _target(2, UserRole.USER)
            repo.set_active.return_value = True
            MockRepo.return_value = repo
            resp = app_client.patch("/admin/users/2/active", json={"is_active": False})
    finally:
        app_client.app.dependency_overrides.pop(get_optional_user, None)
        app_client.app.dependency_overrides.pop(get_db, None)

    assert resp.status_code == 200
    assert resp.json() == {"id": 2, "is_active": False}
    repo.set_active.assert_called_once_with(2, False)
    repo.delete_sessions_for_user.assert_called_once_with(2)


def test_update_user_active_reactivate_does_not_kill_sessions(app_client):
    admin = _make_user(id=1, role=UserRole.ADMIN)
    db = _make_mock_db()
    app_client.app.dependency_overrides[get_optional_user] = lambda: admin
    app_client.app.dependency_overrides[get_db] = lambda: db
    try:
        with patch("src.adapters.api.routers.admin_router.UserRepository") as MockRepo:
            repo = MagicMock()
            repo.get_by_id.return_value = _target(2, UserRole.USER)
            repo.set_active.return_value = True
            MockRepo.return_value = repo
            resp = app_client.patch("/admin/users/2/active", json={"is_active": True})
    finally:
        app_client.app.dependency_overrides.pop(get_optional_user, None)
        app_client.app.dependency_overrides.pop(get_db, None)

    assert resp.status_code == 200
    repo.delete_sessions_for_user.assert_not_called()


def test_update_user_active_rejects_self_change(app_client):
    admin = _make_user(id=1, role=UserRole.ADMIN)
    app_client.app.dependency_overrides[get_optional_user] = lambda: admin
    try:
        resp = app_client.patch("/admin/users/1/active", json={"is_active": False})
    finally:
        app_client.app.dependency_overrides.pop(get_optional_user, None)
    assert resp.status_code == 400


def test_update_user_active_owner_can_never_be_banned(app_client):
    admin = _make_user(id=1, role=UserRole.ADMIN)
    db = _make_mock_db()
    app_client.app.dependency_overrides[get_optional_user] = lambda: admin
    app_client.app.dependency_overrides[get_db] = lambda: db
    try:
        with patch("src.adapters.api.routers.admin_router.UserRepository") as MockRepo:
            repo = MagicMock()
            repo.get_by_id.return_value = _target(2, UserRole.OWNER)
            MockRepo.return_value = repo
            resp = app_client.patch("/admin/users/2/active", json={"is_active": False})
    finally:
        app_client.app.dependency_overrides.pop(get_optional_user, None)
        app_client.app.dependency_overrides.pop(get_db, None)
    assert resp.status_code == 403
    repo.set_active.assert_not_called()


def test_moderator_cannot_ban_another_moderator(app_client):
    moderator = _make_user(id=1, role=UserRole.MODERATOR)
    db = _make_mock_db()
    app_client.app.dependency_overrides[get_optional_user] = lambda: moderator
    app_client.app.dependency_overrides[get_db] = lambda: db
    try:
        with patch("src.adapters.api.routers.admin_router.UserRepository") as MockRepo:
            repo = MagicMock()
            repo.get_by_id.return_value = _target(2, UserRole.MODERATOR)
            MockRepo.return_value = repo
            resp = app_client.patch("/admin/users/2/active", json={"is_active": False})
    finally:
        app_client.app.dependency_overrides.pop(get_optional_user, None)
        app_client.app.dependency_overrides.pop(get_db, None)
    assert resp.status_code == 403


def test_moderator_can_ban_plain_user(app_client):
    moderator = _make_user(id=1, role=UserRole.MODERATOR)
    db = _make_mock_db()
    app_client.app.dependency_overrides[get_optional_user] = lambda: moderator
    app_client.app.dependency_overrides[get_db] = lambda: db
    try:
        with patch("src.adapters.api.routers.admin_router.UserRepository") as MockRepo:
            repo = MagicMock()
            repo.get_by_id.return_value = _target(2, UserRole.USER)
            repo.set_active.return_value = True
            MockRepo.return_value = repo
            resp = app_client.patch("/admin/users/2/active", json={"is_active": False})
    finally:
        app_client.app.dependency_overrides.pop(get_optional_user, None)
        app_client.app.dependency_overrides.pop(get_db, None)
    assert resp.status_code == 200


def test_update_user_active_404_for_missing_user(app_client):
    admin = _make_user(id=1, role=UserRole.ADMIN)
    db = _make_mock_db()
    app_client.app.dependency_overrides[get_optional_user] = lambda: admin
    app_client.app.dependency_overrides[get_db] = lambda: db
    try:
        with patch("src.adapters.api.routers.admin_router.UserRepository") as MockRepo:
            repo = MagicMock()
            repo.get_by_id.return_value = None
            MockRepo.return_value = repo
            resp = app_client.patch("/admin/users/999/active", json={"is_active": False})
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


def test_create_sponsor_deactivates_other_active_sponsors(app_client):
    """Tek 'güncel sponsor' değişmezi korunur — yeni sponsor eklenince
    öncekiler pasife alınmazsa admin panelinde/bültende birden fazla
    is_active=true kayıt oluşur ve arayüz sadece ilkini gösterip
    diğerlerini sessizce gizler (gerçek bir kullanıcı bulgusuydu)."""
    db = _make_mock_db()
    app_client.app.dependency_overrides[get_db] = lambda: db
    payload = {
        "name": "New Sponsor",
        "url": "https://new.example.com",
        "message": "Hello",
        "active_from": datetime.now(timezone.utc).isoformat(),
        "active_until": (datetime.now(timezone.utc) + timedelta(days=30)).isoformat(),
    }
    try:
        resp = app_client.post("/admin/sponsors", json=payload, headers=_HEADERS)
    finally:
        app_client.app.dependency_overrides.pop(get_db, None)

    assert resp.status_code == 201
    db.query.return_value.filter.return_value.update.assert_called_once_with({"is_active": False})


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


def test_activate_sponsor_deactivates_others(app_client):
    db = _make_mock_db()
    orm = _sponsor_orm(id=2, is_active=False)
    db.get.return_value = orm
    app_client.app.dependency_overrides[get_db] = lambda: db
    try:
        resp = app_client.post("/admin/sponsors/2/activate", headers=_HEADERS)
    finally:
        app_client.app.dependency_overrides.pop(get_db, None)

    assert resp.status_code == 200
    assert resp.json()["is_active"] is True
    db.query.return_value.filter.return_value.update.assert_called_once_with({"is_active": False})


def test_activate_nonexistent_sponsor_returns_404(app_client):
    db = _make_mock_db()
    db.get.return_value = None
    app_client.app.dependency_overrides[get_db] = lambda: db
    try:
        resp = app_client.post("/admin/sponsors/999/activate", headers=_HEADERS)
    finally:
        app_client.app.dependency_overrides.pop(get_db, None)

    assert resp.status_code == 404


def test_delete_sponsor_permanently(app_client):
    db = _make_mock_db()
    orm = _sponsor_orm(id=3)
    db.get.return_value = orm
    app_client.app.dependency_overrides[get_db] = lambda: db
    try:
        resp = app_client.delete("/admin/sponsors/3/permanent", headers=_HEADERS)
    finally:
        app_client.app.dependency_overrides.pop(get_db, None)

    assert resp.status_code == 200
    assert resp.json() == {"id": 3, "deleted": True}
    db.delete.assert_called_once_with(orm)
    db.commit.assert_called_once()


def test_delete_nonexistent_sponsor_permanently_returns_404(app_client):
    db = _make_mock_db()
    db.get.return_value = None
    app_client.app.dependency_overrides[get_db] = lambda: db
    try:
        resp = app_client.delete("/admin/sponsors/999/permanent", headers=_HEADERS)
    finally:
        app_client.app.dependency_overrides.pop(get_db, None)

    assert resp.status_code == 404


# ── Manuel tier verme (owner-only, 18 Ağu 2026) ─────────────────────────────────
# Kurucu, ödeme almadan bir kullanıcıya (kendisi dahil) Pro/Kurumsal verebilsin
# diye eklendi. require_owner kullanır (admin YETMEZ) — repo.update_tier()
# zaten var (BILLING_DEV_MODE'un kullandığı aynı metod), stripe_customer_id
# gönderilmez ki is_paying "gerçek ödeme" ile karışmasın.

def test_update_user_tier_rejects_plain_admin_actor(app_client):
    """admin owner değildir — bu endpoint'e giremez (require_owner)."""
    admin = _make_user(id=1, role=UserRole.ADMIN)
    app_client.app.dependency_overrides[get_optional_user] = lambda: admin
    try:
        resp = app_client.patch("/admin/users/2/tier", json={"tier": "pro"})
    finally:
        app_client.app.dependency_overrides.pop(get_optional_user, None)

    assert resp.status_code == 403


def test_update_user_tier_rejects_anonymous(app_client):
    resp = app_client.patch("/admin/users/2/tier", json={"tier": "pro"})
    assert resp.status_code == 401


def test_update_user_tier_success(app_client):
    owner = _make_user(id=1, role=UserRole.OWNER)
    target = _make_user(id=2, role=UserRole.USER, tier=UserTier.FREE)
    db = _make_mock_db()
    app_client.app.dependency_overrides[get_optional_user] = lambda: owner
    app_client.app.dependency_overrides[get_db] = lambda: db
    try:
        with patch("src.adapters.api.routers.admin_router.UserRepository") as MockRepo:
            repo = MagicMock()
            repo.get_by_id.return_value = target
            repo.update_tier.return_value = True
            MockRepo.return_value = repo
            resp = app_client.patch("/admin/users/2/tier", json={"tier": "enterprise"})
    finally:
        app_client.app.dependency_overrides.pop(get_optional_user, None)
        app_client.app.dependency_overrides.pop(get_db, None)

    assert resp.status_code == 200
    assert resp.json() == {"id": 2, "tier": "enterprise"}
    # stripe_customer_id KASITLI gönderilmez — bu manuel bir grant, gerçek
    # ödeme değil, is_paying alanı bundan etkilenmemeli.
    repo.update_tier.assert_called_once_with(2, "enterprise")


def test_update_user_tier_via_api_key(app_client):
    """Makine-makine erişimi (X-API-Key) da owner kadar yetkilidir."""
    db = _make_mock_db()
    app_client.app.dependency_overrides[get_db] = lambda: db
    try:
        with patch("src.adapters.api.routers.admin_router.UserRepository") as MockRepo:
            repo = MagicMock()
            repo.get_by_id.return_value = _make_user(id=2)
            repo.update_tier.return_value = True
            MockRepo.return_value = repo
            resp = app_client.patch("/admin/users/2/tier", json={"tier": "pro"}, headers=_HEADERS)
    finally:
        app_client.app.dependency_overrides.pop(get_db, None)

    assert resp.status_code == 200


def test_update_user_tier_self_change_not_blocked(app_client):
    """Rol değişiminin aksine kendine tier vermek YASAK DEĞİL — owner zaten
    effective_tier ile enterprise muamelesi görüyor, bu sadece kayıt tutarlılığı
    için (kullanıcı açıkça 'kendim dahil' istedi)."""
    owner = _make_user(id=1, role=UserRole.OWNER)
    db = _make_mock_db()
    app_client.app.dependency_overrides[get_optional_user] = lambda: owner
    app_client.app.dependency_overrides[get_db] = lambda: db
    try:
        with patch("src.adapters.api.routers.admin_router.UserRepository") as MockRepo:
            repo = MagicMock()
            repo.get_by_id.return_value = owner
            repo.update_tier.return_value = True
            MockRepo.return_value = repo
            resp = app_client.patch("/admin/users/1/tier", json={"tier": "pro"})
    finally:
        app_client.app.dependency_overrides.pop(get_optional_user, None)
        app_client.app.dependency_overrides.pop(get_db, None)

    assert resp.status_code == 200


def test_update_user_tier_rejects_invalid_tier(app_client):
    owner = _make_user(id=1, role=UserRole.OWNER)
    app_client.app.dependency_overrides[get_optional_user] = lambda: owner
    try:
        resp = app_client.patch("/admin/users/2/tier", json={"tier": "ultra"})
    finally:
        app_client.app.dependency_overrides.pop(get_optional_user, None)

    assert resp.status_code == 400


def test_update_user_tier_404_for_missing_user(app_client):
    owner = _make_user(id=1, role=UserRole.OWNER)
    db = _make_mock_db()
    app_client.app.dependency_overrides[get_optional_user] = lambda: owner
    app_client.app.dependency_overrides[get_db] = lambda: db
    try:
        with patch("src.adapters.api.routers.admin_router.UserRepository") as MockRepo:
            repo = MagicMock()
            repo.get_by_id.return_value = None
            MockRepo.return_value = repo
            resp = app_client.patch("/admin/users/999/tier", json={"tier": "pro"})
    finally:
        app_client.app.dependency_overrides.pop(get_optional_user, None)
        app_client.app.dependency_overrides.pop(get_db, None)

    assert resp.status_code == 404
