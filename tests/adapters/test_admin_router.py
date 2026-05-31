import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock
from src.infrastructure.config.database import get_db


_API_KEY = "dev-key-change-me"
_HEADERS = {"x-api-key": _API_KEY}


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
