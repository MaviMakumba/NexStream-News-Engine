"""/subscriptions endpoint testleri.

12 Eylül 2026 güvenlik turu: bülten uçları daha önce tamamen kimliksizdi —
herkes herkesin adına abone olabiliyor (canlıda denendi: site sahibinin
adresine "BaskaBiriBunuYazdi" anahtar kelimesiyle abonelik açıldı), herkes
herkesi çıkarabiliyor, DELETE'in 200/404 farkı hangi adresin abone olduğunu
ifşa ediyordu. Yeni kurallar:

    POST /subscriptions/           → X-API-Key VEYA e-postası body'dekiyle
                                     eşleşen, e-postası DOĞRULANMIŞ oturum
    DELETE /subscriptions/{email}  → X-API-Key VEYA e-postası eşleşen oturum
    GET /subscriptions/unsubscribe → email + HMAC imzalı token (mail linki)
"""

import pytest
from unittest.mock import MagicMock, patch
from src.domain.models.subscriber import Subscriber
from src.domain.models.user import User, UserRole, UserTier
from src.adapters.api.auth_utils import get_optional_user
from src.adapters.api.routers.subscription_router import _get_repo
from src.adapters.api.subscription_tokens import make_unsubscribe_token
from src.infrastructure.config.settings import settings

API_KEY_HEADERS = {"X-API-Key": settings.api_key}


def _mock_repo(sub=None):
    repo = MagicMock()
    repo.save_subscriber.return_value = sub or Subscriber(
        id=1, email="test@example.com", keywords=[], frequency="daily", language="TR"
    )
    repo.get_by_email.return_value = sub
    repo.deactivate.return_value = True
    repo.update_subscriber.return_value = True
    return repo


def _make_user(email="test@example.com", verified=True, role=UserRole.USER):
    return User(id=7, email=email, password_hash="h", tier=UserTier.FREE, role=role, email_verified=verified)


def _override(app_client, mock_repo, user=None):
    app_client.app.dependency_overrides[_get_repo] = lambda: mock_repo
    app_client.app.dependency_overrides[get_optional_user] = lambda: user


def _clear(app_client):
    app_client.app.dependency_overrides.pop(_get_repo, None)
    app_client.app.dependency_overrides.pop(get_optional_user, None)


def _post_subscribe(app_client, email="test@example.com", **headers):
    with patch("src.adapters.api.routers.subscription_router.get_email_adapter") as mock_email:
        mock_email.return_value.send_welcome.return_value = True
        return app_client.post("/subscriptions/", json={
            "email": email, "keywords": ["beşiktaş"], "frequency": "daily", "language": "TR",
        }, headers=headers)


# ── POST /subscriptions/ ──────────────────────────────────────────────────────

def test_subscribe_anonymous_is_rejected(app_client):
    mock_repo = _mock_repo()
    _override(app_client, mock_repo, user=None)
    try:
        r = _post_subscribe(app_client)
    finally:
        _clear(app_client)
    assert r.status_code == 401
    mock_repo.save_subscriber.assert_not_called()


def test_subscribe_own_verified_email_creates_subscriber(app_client):
    mock_repo = _mock_repo()
    _override(app_client, mock_repo, user=_make_user())
    try:
        r = _post_subscribe(app_client)
    finally:
        _clear(app_client)
    assert r.status_code == 201
    assert r.json()["email"] == "test@example.com"
    mock_repo.save_subscriber.assert_called_once()


def test_subscribe_email_match_is_case_insensitive(app_client):
    mock_repo = _mock_repo()
    _override(app_client, mock_repo, user=_make_user(email="Test@Example.com"))
    try:
        r = _post_subscribe(app_client, email="test@example.com")
    finally:
        _clear(app_client)
    assert r.status_code == 201


def test_subscribe_someone_elses_email_is_forbidden(app_client):
    """Canlıda görülen istismar: site sahibinin adresine başkası abonelik açtı."""
    mock_repo = _mock_repo()
    _override(app_client, mock_repo, user=_make_user(email="attacker@example.com"))
    try:
        r = _post_subscribe(app_client, email="victim@example.com")
    finally:
        _clear(app_client)
    assert r.status_code == 403
    mock_repo.save_subscriber.assert_not_called()


def test_subscribe_requires_verified_email(app_client):
    """Doğrulanmamış hesap = adresin gerçekten o kişiye ait olduğu kanıtlanmamış;
    kurbanın adresiyle hesap açıp günlük digest spam'i başlatmak mümkün olurdu."""
    mock_repo = _mock_repo()
    _override(app_client, mock_repo, user=_make_user(verified=False))
    try:
        r = _post_subscribe(app_client)
    finally:
        _clear(app_client)
    assert r.status_code == 403
    assert "doğrula" in r.json()["detail"].lower() or "verify" in r.json()["detail"].lower()
    mock_repo.save_subscriber.assert_not_called()


def test_subscribe_owner_is_exempt_from_verification(app_client):
    """Owner diğer doğrulama kapılarından (banner, checkout) muaf — burada da."""
    mock_repo = _mock_repo()
    _override(app_client, mock_repo, user=_make_user(verified=False, role=UserRole.OWNER))
    try:
        r = _post_subscribe(app_client)
    finally:
        _clear(app_client)
    assert r.status_code == 201


def test_subscribe_with_api_key_allows_any_email(app_client):
    mock_repo = _mock_repo()
    _override(app_client, mock_repo, user=None)
    try:
        r = _post_subscribe(app_client, email="anyone@example.com", **API_KEY_HEADERS)
    finally:
        _clear(app_client)
    assert r.status_code == 201


def test_subscribe_rejects_invalid_frequency(app_client):
    mock_repo = _mock_repo()
    _override(app_client, mock_repo, user=_make_user(email="x@y.com"))
    try:
        r = app_client.post("/subscriptions/", json={"email": "x@y.com", "frequency": "weekly"})
    finally:
        _clear(app_client)
    assert r.status_code == 400


# ── DELETE /subscriptions/{email} ─────────────────────────────────────────────

def test_unsubscribe_anonymous_is_rejected(app_client):
    mock_repo = _mock_repo()
    _override(app_client, mock_repo, user=None)
    try:
        r = app_client.delete("/subscriptions/test@example.com")
    finally:
        _clear(app_client)
    assert r.status_code == 401
    mock_repo.deactivate.assert_not_called()


def test_unsubscribe_own_email_deactivates(app_client):
    mock_repo = _mock_repo()
    _override(app_client, mock_repo, user=_make_user())
    try:
        r = app_client.delete("/subscriptions/test@example.com")
    finally:
        _clear(app_client)
    assert r.status_code == 200
    mock_repo.deactivate.assert_called_once_with("test@example.com")


def test_unsubscribe_someone_elses_email_is_forbidden(app_client):
    mock_repo = _mock_repo()
    _override(app_client, mock_repo, user=_make_user(email="attacker@example.com"))
    try:
        r = app_client.delete("/subscriptions/victim@example.com")
    finally:
        _clear(app_client)
    assert r.status_code == 403
    mock_repo.deactivate.assert_not_called()


def test_unsubscribe_with_api_key_works_for_any_email(app_client):
    mock_repo = _mock_repo()
    _override(app_client, mock_repo, user=None)
    try:
        r = app_client.delete("/subscriptions/anyone@example.com", headers=API_KEY_HEADERS)
    finally:
        _clear(app_client)
    assert r.status_code == 200


def test_unsubscribe_404_when_not_found(app_client):
    mock_repo = _mock_repo()
    mock_repo.deactivate.return_value = False
    _override(app_client, mock_repo, user=_make_user(email="missing@example.com"))
    try:
        r = app_client.delete("/subscriptions/missing@example.com")
    finally:
        _clear(app_client)
    assert r.status_code == 404


# ── GET /subscriptions/unsubscribe (mail linki) ───────────────────────────────

def _link(email, token=None, lang="TR"):
    token = make_unsubscribe_token(email) if token is None else token
    return f"/subscriptions/unsubscribe?email={email}&token={token}&lang={lang}"


def test_unsubscribe_via_link_deactivates_and_returns_html(app_client):
    mock_repo = _mock_repo()
    _override(app_client, mock_repo)
    try:
        r = app_client.get(_link("test@example.com", lang="TR"))
    finally:
        _clear(app_client)
    assert r.status_code == 200
    assert "text/html" in r.headers["content-type"]
    assert "iptal edildi" in r.text.lower()
    mock_repo.deactivate.assert_called_once_with("test@example.com")


def test_unsubscribe_via_link_english(app_client):
    mock_repo = _mock_repo()
    _override(app_client, mock_repo)
    try:
        r = app_client.get(_link("test@example.com", lang="EN"))
    finally:
        _clear(app_client)
    assert r.status_code == 200
    assert "unsubscribed" in r.text.lower()


def test_unsubscribe_via_link_without_token_does_nothing(app_client):
    """Eski (imzasız) link şekli artık aboneliği KAPATMAZ — adresi bilen herkesin
    başkasını çıkarabildiği açık buydu. Sayfa yine 200 döner (mail istemcisinden
    tıklanıyor) ama 'bulunamadı' mesajı gösterir."""
    mock_repo = _mock_repo()
    _override(app_client, mock_repo)
    try:
        r = app_client.get("/subscriptions/unsubscribe?email=test@example.com&lang=TR")
    finally:
        _clear(app_client)
    assert r.status_code == 200
    assert "bulunamadı" in r.text.lower()
    mock_repo.deactivate.assert_not_called()


def test_unsubscribe_via_link_with_wrong_token_does_nothing(app_client):
    mock_repo = _mock_repo()
    _override(app_client, mock_repo)
    try:
        r = app_client.get(_link("test@example.com", token=make_unsubscribe_token("other@example.com")))
    finally:
        _clear(app_client)
    assert r.status_code == 200
    mock_repo.deactivate.assert_not_called()


def test_unsubscribe_via_link_not_found_still_returns_200_with_message(app_client):
    """Link tıklamaları JSON hata değil, kullanıcı dostu bir sayfa göstermeli."""
    mock_repo = _mock_repo()
    mock_repo.deactivate.return_value = False
    _override(app_client, mock_repo)
    try:
        r = app_client.get(_link("missing@example.com"))
    finally:
        _clear(app_client)
    assert r.status_code == 200
    assert "bulunamadı" in r.text.lower()


def test_unsubscribe_link_route_does_not_collide_with_email_param_route(app_client):
    """'/unsubscribe' bir e-posta adresi olarak yorumlanmamalı (route sırası önemli)."""
    mock_repo = _mock_repo()
    _override(app_client, mock_repo)
    try:
        r = app_client.get(_link("test@example.com"))
    finally:
        _clear(app_client)
    assert r.status_code == 200
    mock_repo.deactivate.assert_called_once_with("test@example.com")
    mock_repo.get_by_email.assert_not_called()


# ── Admin uçları (değişmedi) ─────────────────────────────────────────────────

def test_update_preferences_requires_api_key(app_client):
    r = app_client.patch("/subscriptions/test@example.com", json={"keywords": ["spor"]})
    assert r.status_code == 401


def test_get_subscription_requires_api_key(app_client):
    r = app_client.get("/subscriptions/test@example.com")
    assert r.status_code == 401
