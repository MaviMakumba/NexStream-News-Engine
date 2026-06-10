"""Rol tabanlı admin yetkilendirme testleri (v1.11).

`require_admin` iki yolu kabul eder: paylaşımlı X-API-Key (makine-makine)
ve admin kullanıcı oturumu (users.is_admin VEYA ADMIN_EMAILS bootstrap).
Ek olarak `get_optional_user`'ın X-User-Key çözümlemesi test edilir.
"""

import pytest
from unittest.mock import patch, MagicMock

from fastapi import HTTPException

from src.adapters.api.auth_utils import (
    get_optional_user,
    has_admin_role,
    require_admin,
)
from src.domain.models.user import User, UserTier
from src.infrastructure.config.database import get_db
from src.infrastructure.config.settings import settings


def _make_user(is_admin=False, email="user@test.com", api_key=None):
    return User(
        id=1, email=email, password_hash="h",
        tier=UserTier.FREE, is_admin=is_admin, api_key=api_key,
    )


# ── has_admin_role ────────────────────────────────────────────────────────────

def test_admin_flag_grants_role():
    assert has_admin_role(_make_user(is_admin=True)) is True


def test_regular_user_has_no_role():
    assert has_admin_role(_make_user(is_admin=False)) is False


def test_admin_emails_env_bootstraps_role():
    """DB'de is_admin=false olsa bile ADMIN_EMAILS listesi yetki verir."""
    user = _make_user(is_admin=False, email="Boss@Company.com")
    with patch.object(settings, "admin_emails", "boss@company.com, other@x.com"):
        assert has_admin_role(user) is True


# ── require_admin (unit) ──────────────────────────────────────────────────────

def test_require_admin_accepts_valid_api_key():
    # X-API-Key geçerliyse kullanıcı oturumu hiç gerekmez
    require_admin(x_api_key=settings.api_key, user=None)


def test_require_admin_accepts_admin_session():
    require_admin(x_api_key=None, user=_make_user(is_admin=True))


def test_require_admin_rejects_anonymous_with_401():
    with pytest.raises(HTTPException) as exc:
        require_admin(x_api_key=None, user=None)
    assert exc.value.status_code == 401


def test_require_admin_rejects_non_admin_user_with_403():
    """Kimliği belli ama yetkisiz kullanıcı 403 alır (401 değil)."""
    with pytest.raises(HTTPException) as exc:
        require_admin(x_api_key=None, user=_make_user(is_admin=False))
    assert exc.value.status_code == 403


def test_require_admin_rejects_wrong_api_key():
    with pytest.raises(HTTPException) as exc:
        require_admin(x_api_key="wrong-key", user=None)
    assert exc.value.status_code == 401


# ── require_admin (integration — /admin/usage) ────────────────────────────────

def test_admin_endpoint_accessible_with_admin_session(app_client):
    admin = _make_user(is_admin=True)
    app_client.app.dependency_overrides[get_optional_user] = lambda: admin
    app_client.app.dependency_overrides[get_db] = lambda: MagicMock()
    try:
        with patch("src.adapters.api.routers.admin_router.UserRepository") as MockRepo:
            repo = MagicMock()
            repo.get_usage_stats.return_value = []
            MockRepo.return_value = repo
            resp = app_client.get("/admin/usage")
    finally:
        app_client.app.dependency_overrides.pop(get_optional_user, None)
        app_client.app.dependency_overrides.pop(get_db, None)

    assert resp.status_code == 200


def test_admin_endpoint_403_for_regular_user_session(app_client):
    user = _make_user(is_admin=False)
    app_client.app.dependency_overrides[get_optional_user] = lambda: user
    try:
        resp = app_client.get("/admin/usage")
    finally:
        app_client.app.dependency_overrides.pop(get_optional_user, None)

    assert resp.status_code == 403


# ── X-User-Key kimlik çözümleme ───────────────────────────────────────────────

def test_get_optional_user_resolves_user_key():
    expected = _make_user(api_key="nxs_secret")
    with patch("src.adapters.api.auth_utils.UserRepository") as MockRepo:
        repo = MagicMock()
        repo.get_by_api_key.return_value = expected
        MockRepo.return_value = repo
        result = get_optional_user(x_session_token=None, x_user_key="nxs_secret", db=MagicMock())

    assert result is expected
    repo.get_by_api_key.assert_called_once_with("nxs_secret")


def test_get_optional_user_invalid_key_returns_none():
    with patch("src.adapters.api.auth_utils.UserRepository") as MockRepo:
        repo = MagicMock()
        repo.get_by_api_key.return_value = None
        MockRepo.return_value = repo
        result = get_optional_user(x_session_token=None, x_user_key="nxs_bogus", db=MagicMock())

    assert result is None


def test_get_optional_user_session_takes_priority_over_key():
    """Hem session hem anahtar geldiyse session kazanır."""
    session_user = _make_user(email="session@test.com")
    with patch("src.adapters.api.auth_utils.UserRepository") as MockRepo, \
         patch("src.adapters.api.auth_utils.resolve_session_user", return_value=session_user):
        MockRepo.return_value = MagicMock()
        result = get_optional_user(x_session_token="tok", x_user_key="nxs_k", db=MagicMock())

    assert result is session_user


def test_get_optional_user_anonymous_returns_none():
    result = get_optional_user(x_session_token=None, x_user_key=None, db=MagicMock())
    assert result is None
