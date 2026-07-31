import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock
from src.domain.models.user import User, UserTier, UserRole, UserSession, TIER_DAILY_LIMITS
from src.adapters.api.auth_utils import check_tier_limit, get_optional_user
from src.dependencies import get_news_service
from fastapi import HTTPException


def _make_user(tier=UserTier.FREE, uid=1):
    return User(id=uid, email="u@test.com", password_hash="h", tier=tier)


# ── TIER_DAILY_LIMITS constants ───────────────────────────────────────────────

def test_free_tier_limit_is_100():
    assert TIER_DAILY_LIMITS[UserTier.FREE] == 100


def test_pro_tier_limit_is_2000():
    assert TIER_DAILY_LIMITS[UserTier.PRO] == 2000


def test_enterprise_tier_limit_is_none():
    assert TIER_DAILY_LIMITS[UserTier.ENTERPRISE] is None


# ── check_tier_limit unit tests ───────────────────────────────────────────────

def test_check_tier_limit_allows_free_under_limit():
    from unittest.mock import MagicMock, patch
    user = _make_user(UserTier.FREE)
    with patch("src.adapters.api.auth_utils.UserRepository") as MockRepo:
        repo = MagicMock()
        repo.get_daily_usage_count.return_value = 50
        MockRepo.return_value = repo
        db = MagicMock()
        result = check_tier_limit(user=user, db=db)
    assert result is user


def test_check_tier_limit_blocks_free_at_limit():
    from unittest.mock import MagicMock, patch
    user = _make_user(UserTier.FREE)
    with patch("src.adapters.api.auth_utils.UserRepository") as MockRepo:
        repo = MagicMock()
        repo.get_daily_usage_count.return_value = 100
        MockRepo.return_value = repo
        db = MagicMock()
        with pytest.raises(HTTPException) as exc_info:
            check_tier_limit(user=user, db=db)
    assert exc_info.value.status_code == 429


def test_check_tier_limit_blocks_free_over_limit():
    from unittest.mock import MagicMock, patch
    user = _make_user(UserTier.FREE)
    with patch("src.adapters.api.auth_utils.UserRepository") as MockRepo:
        repo = MagicMock()
        repo.get_daily_usage_count.return_value = 150
        MockRepo.return_value = repo
        db = MagicMock()
        with pytest.raises(HTTPException):
            check_tier_limit(user=user, db=db)


def test_check_tier_limit_allows_pro_under_limit():
    from unittest.mock import MagicMock, patch
    user = _make_user(UserTier.PRO)
    with patch("src.adapters.api.auth_utils.UserRepository") as MockRepo:
        repo = MagicMock()
        repo.get_daily_usage_count.return_value = 1999
        MockRepo.return_value = repo
        db = MagicMock()
        result = check_tier_limit(user=user, db=db)
    assert result is user


def test_check_tier_limit_enterprise_never_blocked():
    from unittest.mock import MagicMock, patch
    user = _make_user(UserTier.ENTERPRISE)
    with patch("src.adapters.api.auth_utils.UserRepository") as MockRepo:
        repo = MagicMock()
        repo.get_daily_usage_count.return_value = 99999
        MockRepo.return_value = repo
        db = MagicMock()
        result = check_tier_limit(user=user, db=db)
    assert result is user


def test_check_tier_limit_anonymous_returns_none():
    from unittest.mock import MagicMock
    db = MagicMock()
    result = check_tier_limit(user=None, db=db)
    assert result is None


def test_check_tier_limit_owner_never_blocked_despite_free_db_tier():
    from unittest.mock import MagicMock, patch
    owner = User(id=9, email="o@test.com", password_hash="h", tier=UserTier.FREE, role=UserRole.OWNER)
    with patch("src.adapters.api.auth_utils.UserRepository") as MockRepo:
        repo = MagicMock()
        repo.get_daily_usage_count.return_value = 99999
        MockRepo.return_value = repo
        db = MagicMock()
        result = check_tier_limit(user=owner, db=db)
    assert result is owner


def test_tier_limit_429_detail_message():
    from unittest.mock import MagicMock, patch
    user = _make_user(UserTier.FREE)
    with patch("src.adapters.api.auth_utils.UserRepository") as MockRepo:
        repo = MagicMock()
        repo.get_daily_usage_count.return_value = 100
        MockRepo.return_value = repo
        db = MagicMock()
        with pytest.raises(HTTPException) as exc_info:
            check_tier_limit(user=user, db=db)
    assert "100" in exc_info.value.detail


# ── Integration tests via v1 router ──────────────────────────────────────────

def test_v1_route_works_when_tier_limit_not_exceeded(app_client):
    mock_service = MagicMock()
    mock_service.list_news_paginated.return_value = []
    app_client.app.dependency_overrides[get_news_service] = lambda: mock_service
    app_client.app.dependency_overrides[check_tier_limit] = lambda: None  # anonymous
    try:
        resp = app_client.get("/api/v1/news")
    finally:
        app_client.app.dependency_overrides.pop(get_news_service, None)
        app_client.app.dependency_overrides.pop(check_tier_limit, None)
    assert resp.status_code == 200


def test_v1_route_blocked_when_tier_limit_exceeded(app_client):
    def _raise_limit():
        raise HTTPException(status_code=429, detail="Daily API limit reached (100 req/day)")

    app_client.app.dependency_overrides[check_tier_limit] = _raise_limit
    try:
        resp = app_client.get("/api/v1/news")
    finally:
        app_client.app.dependency_overrides.pop(check_tier_limit, None)
    assert resp.status_code == 429
