import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
from src.domain.models.subscriber import Subscriber
from src.adapters.api.routers.subscription_router import _get_repo


def _mock_repo(sub=None):
    repo = MagicMock()
    repo.save_subscriber.return_value = sub or Subscriber(
        id=1, email="test@example.com", keywords=[], frequency="daily", language="TR"
    )
    repo.get_by_email.return_value = sub
    repo.deactivate.return_value = True
    repo.update_subscriber.return_value = True
    return repo


def _override(app_client, mock_repo):
    app_client.app.dependency_overrides[_get_repo] = lambda: mock_repo


def _clear(app_client):
    app_client.app.dependency_overrides.pop(_get_repo, None)


def test_subscribe_creates_subscriber(app_client):
    mock_repo = _mock_repo()
    _override(app_client, mock_repo)
    try:
        with patch("src.adapters.api.routers.subscription_router.get_email_adapter") as mock_email:
            mock_email.return_value.send_welcome.return_value = True
            r = app_client.post("/subscriptions/", json={
                "email": "test@example.com",
                "keywords": ["beşiktaş", "fenerbahçe"],
                "frequency": "instant",
                "language": "TR",
            })
    finally:
        _clear(app_client)
    assert r.status_code == 201
    assert r.json()["email"] == "test@example.com"


def test_subscribe_rejects_invalid_frequency(app_client):
    mock_repo = _mock_repo()
    _override(app_client, mock_repo)
    try:
        r = app_client.post("/subscriptions/", json={
            "email": "x@y.com",
            "frequency": "weekly",
        })
    finally:
        _clear(app_client)
    assert r.status_code == 400


def test_unsubscribe_deactivates(app_client):
    mock_repo = _mock_repo()
    _override(app_client, mock_repo)
    try:
        r = app_client.delete("/subscriptions/test@example.com")
    finally:
        _clear(app_client)
    assert r.status_code == 200
    mock_repo.deactivate.assert_called_once_with("test@example.com")


def test_unsubscribe_404_when_not_found(app_client):
    mock_repo = _mock_repo()
    mock_repo.deactivate.return_value = False
    _override(app_client, mock_repo)
    try:
        r = app_client.delete("/subscriptions/missing@example.com")
    finally:
        _clear(app_client)
    assert r.status_code == 404


def test_unsubscribe_via_link_deactivates_and_returns_html(app_client):
    mock_repo = _mock_repo()
    _override(app_client, mock_repo)
    try:
        r = app_client.get("/subscriptions/unsubscribe?email=test@example.com&lang=TR")
    finally:
        _clear(app_client)
    assert r.status_code == 200
    assert "text/html" in r.headers["content-type"]
    assert "İptal edildi" in r.text or "iptal edildi" in r.text
    mock_repo.deactivate.assert_called_once_with("test@example.com")


def test_unsubscribe_via_link_english(app_client):
    mock_repo = _mock_repo()
    _override(app_client, mock_repo)
    try:
        r = app_client.get("/subscriptions/unsubscribe?email=test@example.com&lang=EN")
    finally:
        _clear(app_client)
    assert r.status_code == 200
    assert "unsubscribed" in r.text.lower()


def test_unsubscribe_via_link_not_found_still_returns_200_with_message(app_client):
    """Link tıklamaları JSON hata değil, kullanıcı dostu bir sayfa göstermeli."""
    mock_repo = _mock_repo()
    mock_repo.deactivate.return_value = False
    _override(app_client, mock_repo)
    try:
        r = app_client.get("/subscriptions/unsubscribe?email=missing@example.com")
    finally:
        _clear(app_client)
    assert r.status_code == 200
    assert "bulunamadı" in r.text.lower()


def test_unsubscribe_link_route_does_not_collide_with_email_param_route(app_client):
    """'/unsubscribe' bir e-posta adresi olarak yorumlanmamalı (route sırası önemli)."""
    mock_repo = _mock_repo()
    _override(app_client, mock_repo)
    try:
        r = app_client.get("/subscriptions/unsubscribe?email=test@example.com")
    finally:
        _clear(app_client)
    assert r.status_code == 200
    mock_repo.deactivate.assert_called_once_with("test@example.com")
    mock_repo.get_by_email.assert_not_called()


def test_update_preferences_requires_api_key(app_client):
    r = app_client.patch("/subscriptions/test@example.com", json={"keywords": ["spor"]})
    assert r.status_code == 401


def test_get_subscription_requires_api_key(app_client):
    r = app_client.get("/subscriptions/test@example.com")
    assert r.status_code == 401
