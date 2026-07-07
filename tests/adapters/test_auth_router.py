import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock
from src.domain.models.user import User, UserTier, UserSession, PasswordResetToken


def _make_user(id=1, email="test@example.com", tier=UserTier.FREE, is_active=True):
    return User(id=id, email=email, password_hash="$2b$12$hashed", name="Test User", tier=tier, is_active=is_active)


def _make_session(user_id=1, token="tok123", days=30):
    return UserSession(
        id=1,
        user_id=user_id,
        token=token,
        expires_at=datetime.now(timezone.utc) + timedelta(days=days),
    )


def _expired_session(user_id=1, token="tok_exp"):
    return UserSession(
        id=2,
        user_id=user_id,
        token=token,
        expires_at=datetime.now(timezone.utc) - timedelta(hours=1),
    )


def _make_reset_token(user_id=1, token="reset_tok", minutes=60, used=False):
    return PasswordResetToken(
        id=1,
        user_id=user_id,
        token=token,
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=minutes),
        used=used,
    )


def _expired_reset_token(user_id=1, token="reset_tok_exp"):
    return PasswordResetToken(
        id=2,
        user_id=user_id,
        token=token,
        expires_at=datetime.now(timezone.utc) - timedelta(minutes=1),
        used=False,
    )


@pytest.fixture
def client(app_client):
    return app_client


# ── Register ─────────────────────────────────────────────────────────────────

def test_register_creates_user(client):
    with patch("src.adapters.api.routers.auth_router.UserRepository") as MockRepo:
        repo_instance = MagicMock()
        repo_instance.get_by_email.return_value = None
        repo_instance.create_user.return_value = _make_user()
        repo_instance.create_session.return_value = _make_session()
        MockRepo.return_value = repo_instance

        resp = client.post("/auth/register", json={"email": "test@example.com", "password": "secret123"})

    assert resp.status_code == 201
    data = resp.json()
    assert "token" in data
    assert data["user"]["email"] == "test@example.com"
    assert data["user"]["tier"] == "free"


def test_register_duplicate_email_returns_409(client):
    with patch("src.adapters.api.routers.auth_router.UserRepository") as MockRepo:
        repo_instance = MagicMock()
        repo_instance.get_by_email.return_value = _make_user()
        MockRepo.return_value = repo_instance

        resp = client.post("/auth/register", json={"email": "taken@example.com", "password": "secret123"})

    assert resp.status_code == 409


def test_register_invalid_email_returns_422(client):
    resp = client.post("/auth/register", json={"email": "not-an-email", "password": "secret123"})
    assert resp.status_code == 422


def test_register_tier_defaults_to_free(client):
    with patch("src.adapters.api.routers.auth_router.UserRepository") as MockRepo:
        repo_instance = MagicMock()
        repo_instance.get_by_email.return_value = None
        repo_instance.create_user.return_value = _make_user()
        repo_instance.create_session.return_value = _make_session()
        MockRepo.return_value = repo_instance

        resp = client.post("/auth/register", json={"email": "new@example.com", "password": "pass"})

    assert resp.json()["user"]["tier"] == "free"


def test_register_response_has_token(client):
    with patch("src.adapters.api.routers.auth_router.UserRepository") as MockRepo:
        repo_instance = MagicMock()
        repo_instance.get_by_email.return_value = None
        repo_instance.create_user.return_value = _make_user()
        repo_instance.create_session.return_value = _make_session()
        MockRepo.return_value = repo_instance

        resp = client.post("/auth/register", json={"email": "a@b.com", "password": "pw"})

    assert isinstance(resp.json().get("token"), str)
    assert len(resp.json()["token"]) > 10


# ── Login ─────────────────────────────────────────────────────────────────────

def test_login_success_returns_token(client):
    with patch("src.adapters.api.routers.auth_router.UserRepository") as MockRepo, \
         patch("src.adapters.api.routers.auth_router._verify_password", return_value=True):
        repo_instance = MagicMock()
        repo_instance.get_by_email.return_value = _make_user()
        repo_instance.create_session.return_value = _make_session()
        MockRepo.return_value = repo_instance

        resp = client.post("/auth/login", json={"email": "test@example.com", "password": "secret"})

    assert resp.status_code == 200
    assert "token" in resp.json()


def test_login_wrong_password_returns_401(client):
    with patch("src.adapters.api.routers.auth_router.UserRepository") as MockRepo, \
         patch("src.adapters.api.routers.auth_router._verify_password", return_value=False):
        repo_instance = MagicMock()
        repo_instance.get_by_email.return_value = _make_user()
        MockRepo.return_value = repo_instance

        resp = client.post("/auth/login", json={"email": "test@example.com", "password": "wrong"})

    assert resp.status_code == 401


def test_login_unknown_email_returns_401(client):
    with patch("src.adapters.api.routers.auth_router.UserRepository") as MockRepo:
        repo_instance = MagicMock()
        repo_instance.get_by_email.return_value = None
        MockRepo.return_value = repo_instance

        resp = client.post("/auth/login", json={"email": "ghost@example.com", "password": "pw"})

    assert resp.status_code == 401


# ── Logout ────────────────────────────────────────────────────────────────────

def test_logout_clears_session(client):
    with patch("src.adapters.api.routers.auth_router.UserRepository") as MockRepo:
        repo_instance = MagicMock()
        repo_instance.delete_session.return_value = True
        MockRepo.return_value = repo_instance

        resp = client.post("/auth/logout", headers={"x-session-token": "tok123"})

    assert resp.status_code == 200
    assert "Logged out" in resp.json()["message"]


def test_logout_missing_token_returns_401(client):
    resp = client.post("/auth/logout")
    assert resp.status_code == 401


def test_logout_invalid_token_returns_401(client):
    with patch("src.adapters.api.routers.auth_router.UserRepository") as MockRepo:
        repo_instance = MagicMock()
        repo_instance.delete_session.return_value = False
        MockRepo.return_value = repo_instance

        resp = client.post("/auth/logout", headers={"x-session-token": "bad_token"})

    assert resp.status_code == 401


# ── Me ────────────────────────────────────────────────────────────────────────

def test_me_returns_user_info(client):
    with patch("src.adapters.api.routers.auth_router.UserRepository") as MockRepo:
        repo_instance = MagicMock()
        repo_instance.get_session.return_value = _make_session()
        repo_instance.get_by_id.return_value = _make_user()
        MockRepo.return_value = repo_instance

        resp = client.get("/auth/me", headers={"x-session-token": "tok123"})

    assert resp.status_code == 200
    assert resp.json()["email"] == "test@example.com"
    assert resp.json()["tier"] == "free"


def test_me_missing_token_returns_401(client):
    resp = client.get("/auth/me")
    assert resp.status_code == 401


def test_me_invalid_token_returns_401(client):
    with patch("src.adapters.api.routers.auth_router.UserRepository") as MockRepo:
        repo_instance = MagicMock()
        repo_instance.get_session.return_value = None
        MockRepo.return_value = repo_instance

        resp = client.get("/auth/me", headers={"x-session-token": "invalid"})

    assert resp.status_code == 401


def test_me_expired_session_returns_401(client):
    with patch("src.adapters.api.routers.auth_router.UserRepository") as MockRepo:
        repo_instance = MagicMock()
        repo_instance.get_session.return_value = _expired_session()
        repo_instance.delete_session.return_value = True
        MockRepo.return_value = repo_instance

        resp = client.get("/auth/me", headers={"x-session-token": "tok_exp"})

    assert resp.status_code == 401


# ── Forgot / Reset Password ────────────────────────────────────────────────────

def test_forgot_password_existing_user_sends_email(client):
    with patch("src.adapters.api.routers.auth_router.UserRepository") as MockRepo, \
         patch("src.adapters.api.routers.auth_router.get_email_adapter") as mock_get_adapter:
        repo_instance = MagicMock()
        repo_instance.get_by_email.return_value = _make_user()
        MockRepo.return_value = repo_instance
        mock_adapter = MagicMock()
        mock_adapter.send_password_reset.return_value = True
        mock_get_adapter.return_value = mock_adapter

        resp = client.post("/auth/forgot-password", json={"email": "test@example.com"})

    assert resp.status_code == 200
    repo_instance.create_reset_token.assert_called_once()
    mock_adapter.send_password_reset.assert_called_once()


def test_forgot_password_unknown_email_returns_generic_message(client):
    with patch("src.adapters.api.routers.auth_router.UserRepository") as MockRepo, \
         patch("src.adapters.api.routers.auth_router.get_email_adapter") as mock_get_adapter:
        repo_instance = MagicMock()
        repo_instance.get_by_email.return_value = None
        MockRepo.return_value = repo_instance

        resp = client.post("/auth/forgot-password", json={"email": "ghost@example.com"})

    assert resp.status_code == 200
    repo_instance.create_reset_token.assert_not_called()
    mock_get_adapter.assert_not_called()


def test_forgot_password_inactive_user_no_email(client):
    with patch("src.adapters.api.routers.auth_router.UserRepository") as MockRepo, \
         patch("src.adapters.api.routers.auth_router.get_email_adapter") as mock_get_adapter:
        repo_instance = MagicMock()
        repo_instance.get_by_email.return_value = _make_user(is_active=False)
        MockRepo.return_value = repo_instance

        resp = client.post("/auth/forgot-password", json={"email": "test@example.com"})

    assert resp.status_code == 200
    repo_instance.create_reset_token.assert_not_called()
    mock_get_adapter.assert_not_called()


def test_reset_password_success(client):
    with patch("src.adapters.api.routers.auth_router.UserRepository") as MockRepo:
        repo_instance = MagicMock()
        repo_instance.get_reset_token.return_value = _make_reset_token()
        MockRepo.return_value = repo_instance

        resp = client.post("/auth/reset-password", json={"token": "reset_tok", "password": "newsecret123"})

    assert resp.status_code == 200
    repo_instance.update_password.assert_called_once()
    assert repo_instance.update_password.call_args[0][0] == 1
    repo_instance.mark_reset_token_used.assert_called_once_with("reset_tok")
    repo_instance.delete_sessions_for_user.assert_called_once_with(1)


def test_reset_password_invalid_token_returns_400(client):
    with patch("src.adapters.api.routers.auth_router.UserRepository") as MockRepo:
        repo_instance = MagicMock()
        repo_instance.get_reset_token.return_value = None
        MockRepo.return_value = repo_instance

        resp = client.post("/auth/reset-password", json={"token": "bogus", "password": "newsecret123"})

    assert resp.status_code == 400


def test_reset_password_expired_token_returns_400(client):
    with patch("src.adapters.api.routers.auth_router.UserRepository") as MockRepo:
        repo_instance = MagicMock()
        repo_instance.get_reset_token.return_value = _expired_reset_token()
        MockRepo.return_value = repo_instance

        resp = client.post("/auth/reset-password", json={"token": "reset_tok_exp", "password": "newsecret123"})

    assert resp.status_code == 400
    repo_instance.update_password.assert_not_called()


def test_reset_password_used_token_returns_400(client):
    with patch("src.adapters.api.routers.auth_router.UserRepository") as MockRepo:
        repo_instance = MagicMock()
        repo_instance.get_reset_token.return_value = _make_reset_token(used=True)
        MockRepo.return_value = repo_instance

        resp = client.post("/auth/reset-password", json={"token": "reset_tok", "password": "newsecret123"})

    assert resp.status_code == 400
    repo_instance.update_password.assert_not_called()
