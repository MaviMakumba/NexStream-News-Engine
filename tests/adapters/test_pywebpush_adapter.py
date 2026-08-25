"""PyWebPushAdapter testleri — pywebpush.webpush() mock'lanır, gerçek HTTP çağrısı yok."""

import logging
from unittest.mock import patch, MagicMock

from pywebpush import WebPushException

from src.domain.models.push_subscription import PushSubscription


def _sub():
    return PushSubscription(
        email="me@test.com", endpoint="https://push.example.com/abc",
        p256dh="p256dh-key", auth="auth-secret",
    )


def test_send_success_returns_true():
    from src.adapters.notifications.pywebpush_adapter import PyWebPushAdapter
    adapter = PyWebPushAdapter()
    with patch("src.adapters.notifications.pywebpush_adapter.webpush") as mock_webpush:
        result = adapter.send(_sub(), title="Başlık", body="Gövde", url="https://x.com/1")

    assert result is True
    mock_webpush.assert_called_once()
    call_kwargs = mock_webpush.call_args.kwargs
    assert call_kwargs["subscription_info"]["endpoint"] == "https://push.example.com/abc"
    assert call_kwargs["subscription_info"]["keys"] == {"p256dh": "p256dh-key", "auth": "auth-secret"}


def test_send_expired_subscription_returns_false_without_logging(caplog):
    from src.adapters.notifications.pywebpush_adapter import PyWebPushAdapter
    caplog.set_level(logging.WARNING)
    adapter = PyWebPushAdapter()
    exc = WebPushException("gone", response=MagicMock(status_code=410))
    with patch("src.adapters.notifications.pywebpush_adapter.webpush", side_effect=exc):
        result = adapter.send(_sub(), title="t", body="b", url="https://x.com/1")

    assert result is False
    assert "gönderilemedi" not in caplog.text


def test_send_not_found_subscription_returns_false():
    from src.adapters.notifications.pywebpush_adapter import PyWebPushAdapter
    adapter = PyWebPushAdapter()
    exc = WebPushException("not found", response=MagicMock(status_code=404))
    with patch("src.adapters.notifications.pywebpush_adapter.webpush", side_effect=exc):
        result = adapter.send(_sub(), title="t", body="b", url="https://x.com/1")

    assert result is False


def test_send_server_error_returns_false_and_logs(caplog):
    from src.adapters.notifications.pywebpush_adapter import PyWebPushAdapter
    caplog.set_level(logging.WARNING)
    adapter = PyWebPushAdapter()
    exc = WebPushException("server error", response=MagicMock(status_code=500))
    with patch("src.adapters.notifications.pywebpush_adapter.webpush", side_effect=exc):
        result = adapter.send(_sub(), title="t", body="b", url="https://x.com/1")

    assert result is False
    assert "gönderilemedi" in caplog.text


def test_send_exception_without_response_returns_false():
    from src.adapters.notifications.pywebpush_adapter import PyWebPushAdapter
    adapter = PyWebPushAdapter()
    exc = WebPushException("network error", response=None)
    with patch("src.adapters.notifications.pywebpush_adapter.webpush", side_effect=exc):
        result = adapter.send(_sub(), title="t", body="b", url="https://x.com/1")

    assert result is False
