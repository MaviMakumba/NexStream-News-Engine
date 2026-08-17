"""Billing dev-mode (BILLING_DEV_MODE) testleri — v1.11.

Dev modda /billing/checkout Stripe'a gitmeden tier'ı anında günceller;
/billing/dev/downgrade tier'ı Free'ye çeker. Flag kapalıyken her iki yol
da eski (Stripe) davranışını korur.
"""

from unittest.mock import patch, MagicMock

from src.adapters.api.auth_utils import get_current_user, get_optional_user
from src.domain.models.user import User, UserTier, UserRole
from src.infrastructure.config.database import get_db


def _make_user(tier=UserTier.FREE, email_verified=True, role=UserRole.USER):
    return User(id=1, email="dev@test.com", password_hash="h", tier=tier, email_verified=email_verified, role=role)


def _override(app_client, user):
    app_client.app.dependency_overrides[get_current_user] = lambda: user
    app_client.app.dependency_overrides[get_optional_user] = lambda: user
    app_client.app.dependency_overrides[get_db] = lambda: MagicMock()


def _clear(app_client):
    for dep in (get_current_user, get_optional_user, get_db):
        app_client.app.dependency_overrides.pop(dep, None)


def _checkout_payload(tier="pro"):
    return {
        "tier": tier,
        "success_url": "http://localhost:3000/account",
        "cancel_url": "http://localhost:3000/account",
    }


# ── Dev mode AÇIK ─────────────────────────────────────────────────────────────

def test_dev_checkout_upgrades_tier_without_stripe(app_client):
    _override(app_client, _make_user())
    try:
        with patch("src.adapters.api.routers.billing_router.settings") as ms, \
             patch("src.adapters.api.routers.billing_router.UserRepository") as MockRepo:
            ms.billing_dev_mode = True
            repo = MagicMock()
            MockRepo.return_value = repo
            resp = app_client.post("/billing/checkout", json=_checkout_payload("pro"))
    finally:
        _clear(app_client)

    assert resp.status_code == 200
    data = resp.json()
    assert data["dev_mode"] is True
    assert data["tier"] == "pro"
    assert data["url"] == "http://localhost:3000/account"
    repo.update_tier.assert_called_once_with(1, "pro")


def test_dev_checkout_enterprise(app_client):
    _override(app_client, _make_user())
    try:
        with patch("src.adapters.api.routers.billing_router.settings") as ms, \
             patch("src.adapters.api.routers.billing_router.UserRepository") as MockRepo:
            ms.billing_dev_mode = True
            MockRepo.return_value = MagicMock()
            resp = app_client.post("/billing/checkout", json=_checkout_payload("enterprise"))
    finally:
        _clear(app_client)

    assert resp.status_code == 200
    assert resp.json()["tier"] == "enterprise"


def test_dev_checkout_blocked_when_email_not_verified(app_client):
    """Dev mode ödeme simülasyonunu atlatmaz — doğrulama kontrolü checkout'un başında."""
    _override(app_client, _make_user(email_verified=False))
    try:
        with patch("src.adapters.api.routers.billing_router.settings") as ms:
            ms.billing_dev_mode = True
            resp = app_client.post("/billing/checkout", json=_checkout_payload("pro"))
    finally:
        _clear(app_client)

    assert resp.status_code == 403


def test_dev_checkout_invalid_tier_still_400(app_client):
    """Tier doğrulaması dev modda da geçerlidir."""
    _override(app_client, _make_user())
    try:
        with patch("src.adapters.api.routers.billing_router.settings") as ms:
            ms.billing_dev_mode = True
            resp = app_client.post("/billing/checkout", json=_checkout_payload("free"))
    finally:
        _clear(app_client)

    assert resp.status_code == 400


def test_checkout_rejects_owner_with_400_even_when_unverified(app_client):
    """Owner'ın satın alacağı bir şey yok; email_verified=False olsa da 403
    yerine anlamlı bir 400 alır (unrelated doğrulama gate'ine hiç girmemeli)."""
    owner = _make_user(role=UserRole.OWNER, email_verified=False)
    _override(app_client, owner)
    try:
        with patch("src.adapters.api.routers.billing_router.settings") as ms:
            ms.billing_dev_mode = True
            resp = app_client.post("/billing/checkout", json={
                "tier": "pro", "success_url": "http://x", "cancel_url": "http://x",
            })
    finally:
        _clear(app_client)
    assert resp.status_code == 400


def test_dev_downgrade_sets_free(app_client):
    _override(app_client, _make_user(UserTier.PRO))
    try:
        with patch("src.adapters.api.routers.billing_router.settings") as ms, \
             patch("src.adapters.api.routers.billing_router.UserRepository") as MockRepo:
            ms.billing_dev_mode = True
            repo = MagicMock()
            MockRepo.return_value = repo
            resp = app_client.post("/billing/dev/downgrade")
    finally:
        _clear(app_client)

    assert resp.status_code == 200
    assert resp.json()["tier"] == "free"
    repo.update_tier.assert_called_once_with(1, "free")


# ── /billing/config ───────────────────────────────────────────────────────────

def test_billing_config_is_public_and_reports_mode(app_client):
    with patch("src.adapters.api.routers.billing_router.settings") as ms:
        ms.billing_dev_mode = True
        ms.stripe_secret_key = ""
        resp = app_client.get("/billing/config")

    assert resp.status_code == 200
    assert resp.json() == {"dev_mode": True, "stripe_configured": False}


# ── Dev mode KAPALI ───────────────────────────────────────────────────────────

def test_checkout_falls_back_to_stripe_when_dev_mode_off(app_client):
    """Flag kapalıyken Stripe yapılandırması yoksa 503 (eski davranış)."""
    _override(app_client, _make_user())
    try:
        with patch("src.adapters.api.routers.billing_router.settings") as ms:
            ms.billing_dev_mode = False
            ms.stripe_secret_key = ""
            resp = app_client.post("/billing/checkout", json=_checkout_payload("pro"))
    finally:
        _clear(app_client)

    assert resp.status_code == 503


def test_dev_downgrade_404_when_dev_mode_off(app_client):
    _override(app_client, _make_user(UserTier.PRO))
    try:
        with patch("src.adapters.api.routers.billing_router.settings") as ms:
            ms.billing_dev_mode = False
            resp = app_client.post("/billing/dev/downgrade")
    finally:
        _clear(app_client)

    assert resp.status_code == 404


def test_dev_downgrade_requires_auth(app_client):
    resp = app_client.post("/billing/dev/downgrade")
    assert resp.status_code == 401
