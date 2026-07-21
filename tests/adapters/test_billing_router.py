import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock
from src.domain.models.user import User, UserTier, UserSession
from src.adapters.api.auth_utils import get_current_user, get_optional_user


def _make_user(stripe_id=None, tier=UserTier.FREE, email_verified=True):
    return User(
        id=1, email="pay@test.com", password_hash="h",
        tier=tier, stripe_customer_id=stripe_id, email_verified=email_verified,
    )


def _override_user(app_client, user):
    app_client.app.dependency_overrides[get_current_user] = lambda: user
    app_client.app.dependency_overrides[get_optional_user] = lambda: user


def _clear_overrides(app_client):
    app_client.app.dependency_overrides.pop(get_current_user, None)
    app_client.app.dependency_overrides.pop(get_optional_user, None)


# ── Checkout ──────────────────────────────────────────────────────────────────

def test_checkout_requires_auth(app_client):
    resp = app_client.post("/billing/checkout", json={
        "tier": "pro",
        "success_url": "https://example.com/success",
        "cancel_url": "https://example.com/cancel",
    })
    assert resp.status_code == 401


def test_checkout_503_when_stripe_not_configured(app_client):
    _override_user(app_client, _make_user())
    try:
        with patch("src.adapters.api.routers.billing_router.settings") as ms:
            ms.stripe_secret_key = ""
            ms.billing_dev_mode = False
            resp = app_client.post("/billing/checkout", json={
                "tier": "pro",
                "success_url": "https://example.com/s",
                "cancel_url": "https://example.com/c",
            })
    finally:
        _clear_overrides(app_client)
    assert resp.status_code == 503


def test_checkout_blocked_when_email_not_verified(app_client):
    _override_user(app_client, _make_user(email_verified=False))
    try:
        with patch("src.adapters.api.routers.billing_router.settings") as ms:
            ms.stripe_secret_key = "sk_test_xxx"
            ms.billing_dev_mode = False
            resp = app_client.post("/billing/checkout", json={
                "tier": "pro",
                "success_url": "https://example.com/s",
                "cancel_url": "https://example.com/c",
            })
    finally:
        _clear_overrides(app_client)
    assert resp.status_code == 403


def test_checkout_invalid_tier_returns_400(app_client):
    _override_user(app_client, _make_user())
    try:
        with patch("src.adapters.api.routers.billing_router.settings") as ms:
            ms.stripe_secret_key = "sk_test_xxx"
            ms.billing_dev_mode = False
            ms.stripe_pro_price_id = ""
            ms.stripe_enterprise_price_id = ""
            mock_stripe = MagicMock()
            with patch("src.adapters.api.routers.billing_router._require_stripe", return_value=mock_stripe):
                resp = app_client.post("/billing/checkout", json={
                    "tier": "invalid_tier",
                    "success_url": "https://example.com/s",
                    "cancel_url": "https://example.com/c",
                })
    finally:
        _clear_overrides(app_client)
    assert resp.status_code == 400


def test_checkout_creates_stripe_session(app_client):
    mock_stripe = MagicMock()
    mock_stripe.checkout.Session.create.return_value = MagicMock(url="https://checkout.stripe.com/pay/xxx")
    _override_user(app_client, _make_user())
    try:
        with patch("src.adapters.api.routers.billing_router.settings") as ms:
            ms.stripe_secret_key = "sk_test_xxx"
            ms.billing_dev_mode = False
            ms.stripe_pro_price_id = "price_pro_123"
            ms.stripe_enterprise_price_id = "price_ent_456"
            with patch("src.adapters.api.routers.billing_router._require_stripe", return_value=mock_stripe):
                resp = app_client.post("/billing/checkout", json={
                    "tier": "pro",
                    "success_url": "https://example.com/s",
                    "cancel_url": "https://example.com/c",
                })
    finally:
        _clear_overrides(app_client)
    assert resp.status_code == 200
    assert "url" in resp.json()
    assert "stripe.com" in resp.json()["url"]


def test_checkout_returns_url(app_client):
    mock_stripe = MagicMock()
    mock_stripe.checkout.Session.create.return_value = MagicMock(url="https://checkout.stripe.com/pay/abc123")
    _override_user(app_client, _make_user())
    try:
        with patch("src.adapters.api.routers.billing_router.settings") as ms:
            ms.stripe_secret_key = "sk_test"
            ms.billing_dev_mode = False
            ms.stripe_pro_price_id = "price_pro"
            ms.stripe_enterprise_price_id = "price_ent"
            with patch("src.adapters.api.routers.billing_router._require_stripe", return_value=mock_stripe):
                resp = app_client.post("/billing/checkout", json={
                    "tier": "enterprise",
                    "success_url": "https://example.com/s",
                    "cancel_url": "https://example.com/c",
                })
    finally:
        _clear_overrides(app_client)
    assert resp.json()["url"].startswith("https://")


# ── Webhook ───────────────────────────────────────────────────────────────────

def test_webhook_invalid_signature_returns_400(app_client):
    import stripe as _stripe
    mock_stripe = MagicMock()
    mock_stripe.error.SignatureVerificationError = _stripe.error.SignatureVerificationError
    mock_stripe.Webhook.construct_event.side_effect = _stripe.error.SignatureVerificationError("bad sig", "sig", "body")

    with patch("src.adapters.api.routers.billing_router.settings") as ms:
        ms.stripe_secret_key = "sk_test"
        ms.stripe_webhook_secret = "whsec_test"
        with patch("src.adapters.api.routers.billing_router._require_stripe", return_value=mock_stripe):
            resp = app_client.post(
                "/billing/webhook",
                content=b'{"type":"test"}',
                headers={"stripe-signature": "bad"},
            )
    assert resp.status_code == 400


def test_webhook_handles_subscription_created(app_client):
    event = {
        "type": "customer.subscription.created",
        "data": {
            "object": {
                "customer": "cus_xxx",
                "metadata": {"user_id": "1", "tier": "pro"},
            }
        },
    }
    mock_stripe = MagicMock()
    mock_stripe.Webhook.construct_event.return_value = event

    with patch("src.adapters.api.routers.billing_router.settings") as ms:
        ms.stripe_secret_key = "sk_test"
        ms.stripe_webhook_secret = "whsec_test"
        with patch("src.adapters.api.routers.billing_router._require_stripe", return_value=mock_stripe), \
             patch("src.adapters.api.routers.billing_router._handle_subscription_activated") as mock_handle:
            resp = app_client.post(
                "/billing/webhook",
                content=b'{}',
                headers={"stripe-signature": "valid"},
            )
    assert resp.status_code == 200
    mock_handle.assert_called_once()


def test_webhook_handles_subscription_cancelled(app_client):
    event = {
        "type": "customer.subscription.deleted",
        "data": {
            "object": {
                "customer": "cus_xxx",
                "metadata": {"user_id": "1"},
            }
        },
    }
    mock_stripe = MagicMock()
    mock_stripe.Webhook.construct_event.return_value = event

    with patch("src.adapters.api.routers.billing_router.settings") as ms:
        ms.stripe_secret_key = "sk_test"
        ms.stripe_webhook_secret = "whsec_test"
        with patch("src.adapters.api.routers.billing_router._require_stripe", return_value=mock_stripe), \
             patch("src.adapters.api.routers.billing_router._handle_subscription_cancelled") as mock_handle:
            resp = app_client.post(
                "/billing/webhook",
                content=b'{}',
                headers={"stripe-signature": "valid"},
            )
    assert resp.status_code == 200
    mock_handle.assert_called_once()


# ── Portal ────────────────────────────────────────────────────────────────────

def test_portal_requires_auth(app_client):
    resp = app_client.get("/billing/portal")
    assert resp.status_code == 401


def test_portal_no_stripe_customer_returns_404(app_client):
    mock_stripe = MagicMock()
    _override_user(app_client, _make_user(stripe_id=None))
    try:
        with patch("src.adapters.api.routers.billing_router.settings") as ms:
            ms.stripe_secret_key = "sk_test"
            with patch("src.adapters.api.routers.billing_router._require_stripe", return_value=mock_stripe):
                resp = app_client.get("/billing/portal")
    finally:
        _clear_overrides(app_client)
    assert resp.status_code == 404


def test_portal_returns_url(app_client):
    mock_stripe = MagicMock()
    mock_stripe.billing_portal.Session.create.return_value = MagicMock(url="https://billing.stripe.com/p/xxx")
    _override_user(app_client, _make_user(stripe_id="cus_abc"))
    try:
        with patch("src.adapters.api.routers.billing_router.settings") as ms:
            ms.stripe_secret_key = "sk_test"
            with patch("src.adapters.api.routers.billing_router._require_stripe", return_value=mock_stripe):
                resp = app_client.get("/billing/portal")
    finally:
        _clear_overrides(app_client)
    assert resp.status_code == 200
    assert "url" in resp.json()
