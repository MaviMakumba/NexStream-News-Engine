import pytest
from unittest.mock import patch, MagicMock
from src.infrastructure.config.database import get_db
from src.adapters.repositories.orm_models import ContactMessageORM


@pytest.fixture
def client(app_client):
    return app_client


@pytest.fixture
def db(client):
    mock_db = MagicMock()
    client.app.dependency_overrides[get_db] = lambda: mock_db
    yield mock_db
    client.app.dependency_overrides.pop(get_db, None)


def _payload(**overrides):
    payload = {
        "name": "Ada Lovelace",
        "email": "ada@example.com",
        "category": "general",
        "message": "Merhaba, bir sorum var.",
        "language": "TR",
    }
    payload.update(overrides)
    return payload


def test_contact_sends_email_to_configured_recipient(client):
    with patch("src.adapters.api.routers.contact_router.settings") as mock_settings, \
         patch("src.adapters.api.routers.contact_router.get_email_adapter") as mock_get_adapter:
        mock_settings.contact_recipient_email = "owner@nexstreamnews.com"
        mock_adapter = MagicMock()
        mock_adapter.send_contact_message.return_value = True
        mock_get_adapter.return_value = mock_adapter

        resp = client.post("/contact", json=_payload())

    assert resp.status_code == 200
    assert resp.json() == {"success": True}
    mock_adapter.send_contact_message.assert_called_once_with(
        to="owner@nexstreamnews.com",
        name="Ada Lovelace",
        from_email="ada@example.com",
        category="general",
        message="Merhaba, bir sorum var.",
        language="TR",
    )


def test_contact_returns_503_when_recipient_not_configured(client):
    with patch("src.adapters.api.routers.contact_router.settings") as mock_settings:
        mock_settings.contact_recipient_email = ""
        resp = client.post("/contact", json=_payload())

    assert resp.status_code == 503


def test_contact_returns_502_when_email_provider_fails(client):
    with patch("src.adapters.api.routers.contact_router.settings") as mock_settings, \
         patch("src.adapters.api.routers.contact_router.get_email_adapter") as mock_get_adapter:
        mock_settings.contact_recipient_email = "owner@nexstreamnews.com"
        mock_adapter = MagicMock()
        mock_adapter.send_contact_message.return_value = False
        mock_get_adapter.return_value = mock_adapter

        resp = client.post("/contact", json=_payload())

    assert resp.status_code == 502


def test_contact_rejects_invalid_email(client):
    resp = client.post("/contact", json=_payload(email="not-an-email"))
    assert resp.status_code == 422


def test_contact_rejects_invalid_category(client):
    resp = client.post("/contact", json=_payload(category="something-else"))
    assert resp.status_code == 422


def test_contact_rejects_empty_message(client):
    resp = client.post("/contact", json=_payload(message=""))
    assert resp.status_code == 422


def test_contact_message_persisted_to_db(client, db):
    with patch("src.adapters.api.routers.contact_router.settings") as mock_settings, \
         patch("src.adapters.api.routers.contact_router.get_email_adapter") as mock_get_adapter:
        mock_settings.contact_recipient_email = "owner@nexstreamnews.com"
        mock_adapter = MagicMock()
        mock_adapter.send_contact_message.return_value = True
        mock_get_adapter.return_value = mock_adapter

        resp = client.post("/contact", json=_payload())

    assert resp.status_code == 200
    db.add.assert_called_once()
    saved = db.add.call_args[0][0]
    assert isinstance(saved, ContactMessageORM)
    assert saved.name == "Ada Lovelace"
    assert saved.email == "ada@example.com"
    assert saved.category == "general"
    assert saved.message == "Merhaba, bir sorum var."
    assert saved.language == "TR"
    db.commit.assert_called_once()


def test_contact_message_persisted_even_when_email_delivery_fails(client, db):
    """Roadmap madde 26: e-posta spam'e düşse/gecikse/başarısız olsa bile
    mesaj admin panelden görülebilsin diye kaybolmamalı."""
    with patch("src.adapters.api.routers.contact_router.settings") as mock_settings, \
         patch("src.adapters.api.routers.contact_router.get_email_adapter") as mock_get_adapter:
        mock_settings.contact_recipient_email = "owner@nexstreamnews.com"
        mock_adapter = MagicMock()
        mock_adapter.send_contact_message.return_value = False
        mock_get_adapter.return_value = mock_adapter

        resp = client.post("/contact", json=_payload())

    assert resp.status_code == 502
    db.add.assert_called_once()
    db.commit.assert_called_once()


def test_contact_message_persisted_even_when_recipient_not_configured(client, db):
    with patch("src.adapters.api.routers.contact_router.settings") as mock_settings:
        mock_settings.contact_recipient_email = ""
        resp = client.post("/contact", json=_payload())

    assert resp.status_code == 503
    db.add.assert_called_once()
    db.commit.assert_called_once()


def test_contact_defaults_category_to_general_and_name_optional(client):
    with patch("src.adapters.api.routers.contact_router.settings") as mock_settings, \
         patch("src.adapters.api.routers.contact_router.get_email_adapter") as mock_get_adapter:
        mock_settings.contact_recipient_email = "owner@nexstreamnews.com"
        mock_adapter = MagicMock()
        mock_adapter.send_contact_message.return_value = True
        mock_get_adapter.return_value = mock_adapter

        resp = client.post("/contact", json={"email": "ada@example.com", "message": "Selam"})

    assert resp.status_code == 200
    call_kwargs = mock_adapter.send_contact_message.call_args[1]
    assert call_kwargs["category"] == "general"
    assert call_kwargs["name"] == ""
