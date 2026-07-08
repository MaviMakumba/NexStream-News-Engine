import pytest
from unittest.mock import patch, MagicMock
from src.adapters.notifications.email_adapter import ConsoleEmailAdapter, ResendEmailAdapter, get_email_adapter
from src.domain.models.article import Article


def _article():
    a = Article(title="Test Haberi", source="TRT", url="http://test.com", content="içerik")
    a.summary = "Özet"
    a.sentiment_label = "Positive"
    a.topic = "Sports"
    a.id = 1
    return a


def test_console_adapter_send_digest_returns_true():
    adapter = ConsoleEmailAdapter()
    assert adapter.send_digest("user@test.com", [_article()], "TR") is True


def test_console_adapter_send_alert_returns_true():
    adapter = ConsoleEmailAdapter()
    assert adapter.send_alert("user@test.com", _article(), "beşiktaş", "TR") is True


def test_console_adapter_send_welcome_returns_true():
    adapter = ConsoleEmailAdapter()
    assert adapter.send_welcome("user@test.com", "EN") is True


def test_resend_adapter_sends_post_request():
    with patch("src.adapters.notifications.email_adapter.settings") as mock_settings:
        mock_settings.resend_api_key = "re_test_key"
        mock_settings.email_from = "NexStream <no-reply@test.com>"
        adapter = ResendEmailAdapter()

        mock_response = MagicMock()
        mock_response.status_code = 200
        with patch("requests.post", return_value=mock_response) as mock_post:
            result = adapter.send_digest("user@test.com", [_article()], "TR")

    assert result is True
    mock_post.assert_called_once()
    call_kwargs = mock_post.call_args[1]
    assert call_kwargs["json"]["to"] == ["user@test.com"]


def test_resend_adapter_returns_false_on_error():
    with patch("src.adapters.notifications.email_adapter.settings") as mock_settings:
        mock_settings.resend_api_key = "re_test_key"
        mock_settings.email_from = "NexStream <no-reply@test.com>"
        adapter = ResendEmailAdapter()

        mock_response = MagicMock()
        mock_response.status_code = 429
        mock_response.text = "Too Many Requests"
        with patch("requests.post", return_value=mock_response):
            result = adapter.send_alert("user@test.com", _article(), "keyword", "TR")

    assert result is False


def test_get_email_adapter_returns_console_without_api_key():
    with patch("src.adapters.notifications.email_adapter.settings") as mock_settings:
        mock_settings.resend_api_key = ""
        adapter = get_email_adapter()
    assert isinstance(adapter, ConsoleEmailAdapter)


def test_get_email_adapter_returns_resend_with_api_key():
    with patch("src.adapters.notifications.email_adapter.settings") as mock_settings:
        mock_settings.resend_api_key = "re_prod_key"
        mock_settings.email_from = "NexStream <x@y.com>"
        adapter = get_email_adapter()
    assert isinstance(adapter, ResendEmailAdapter)
