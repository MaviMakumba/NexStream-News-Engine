import pytest
from unittest.mock import patch, MagicMock
from src.adapters.notifications.email_adapter import ConsoleEmailAdapter, ResendEmailAdapter, SmtpEmailAdapter, get_email_adapter
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
        mock_settings.email_provider = "auto"
        mock_settings.resend_api_key = ""
        mock_settings.smtp_user = ""
        mock_settings.smtp_password = ""
        adapter = get_email_adapter()
    assert isinstance(adapter, ConsoleEmailAdapter)


def test_get_email_adapter_returns_resend_with_api_key():
    with patch("src.adapters.notifications.email_adapter.settings") as mock_settings:
        mock_settings.email_provider = "auto"
        mock_settings.resend_api_key = "re_prod_key"
        mock_settings.email_from = "NexStream <x@y.com>"
        mock_settings.smtp_user = ""
        mock_settings.smtp_password = ""
        adapter = get_email_adapter()
    assert isinstance(adapter, ResendEmailAdapter)


# ── HTML injection (güvenlik denetimi) ──────────────────────────────────────────

def _malicious_article():
    a = Article(
        title='<script>alert(1)</script><a href="http://phish.example">tıkla</a>',
        source="Kötücül Kaynak", url="http://test.com", content="içerik",
    )
    a.summary = '<img src=x onerror=alert(2)>'
    a.sentiment_label = "Positive"
    a.topic = "Sports"
    a.id = 1
    return a


def test_digest_html_escapes_malicious_article_title():
    from src.adapters.notifications.email_adapter import _digest_html
    out = _digest_html("user@test.com", [_malicious_article()], "TR")
    assert "<script>" not in out
    assert "<img" not in out  # onerror='...' tetiklenmesi için gerçek bir <img> tag'i gerekir
    assert "&lt;script&gt;" in out


def test_alert_html_escapes_malicious_article_title():
    from src.adapters.notifications.email_adapter import _alert_html
    out = _alert_html(_malicious_article(), "keyword", "TR")
    assert "<script>" not in out
    assert "&lt;script&gt;" in out


def test_sponsor_html_escapes_malicious_fields():
    from src.adapters.notifications.email_adapter import _sponsor_html
    sponsor = MagicMock()
    sponsor.url = "http://ok.example"
    sponsor.name = '<script>alert(3)</script>'
    sponsor.message = '<img src=x onerror=alert(4)>'
    out = _sponsor_html(sponsor, "TR")
    assert "<script>" not in out
    assert "<img" not in out  # onerror='...' tetiklenmesi için gerçek bir <img> tag'i gerekir


# ── SmtpEmailAdapter + EMAIL_PROVIDER seçim matrisi ─────────────────────────────

def test_smtp_adapter_sends_via_starttls_and_login():
    with patch("src.adapters.notifications.email_adapter.settings") as mock_settings:
        mock_settings.smtp_host = "smtp.gmail.com"
        mock_settings.smtp_port = 587
        mock_settings.smtp_user = "me@gmail.com"
        mock_settings.smtp_password = "app-password"
        mock_settings.smtp_from = ""
        mock_settings.email_from = "NexStream <no-reply@test.com>"
        mock_settings.smtp_starttls = True
        adapter = SmtpEmailAdapter()

        mock_server = MagicMock()
        mock_smtp_cm = MagicMock()
        mock_smtp_cm.__enter__.return_value = mock_server
        with patch("smtplib.SMTP", return_value=mock_smtp_cm) as mock_smtp:
            result = adapter.send_welcome("user@test.com", "TR")

    assert result is True
    mock_smtp.assert_called_once_with("smtp.gmail.com", 587, timeout=10)
    mock_server.starttls.assert_called_once()
    mock_server.login.assert_called_once_with("me@gmail.com", "app-password")
    mock_server.sendmail.assert_called_once()
    call_args = mock_server.sendmail.call_args[0]
    assert call_args[0] == "me@gmail.com"
    assert call_args[1] == ["user@test.com"]


def test_smtp_adapter_skips_starttls_when_disabled():
    with patch("src.adapters.notifications.email_adapter.settings") as mock_settings:
        mock_settings.smtp_host = "localhost"
        mock_settings.smtp_port = 25
        mock_settings.smtp_user = "me@test.com"
        mock_settings.smtp_password = "x"
        mock_settings.smtp_from = ""
        mock_settings.email_from = "NexStream <no-reply@test.com>"
        mock_settings.smtp_starttls = False
        adapter = SmtpEmailAdapter()
        mock_server = MagicMock()
        mock_smtp_cm = MagicMock()
        mock_smtp_cm.__enter__.return_value = mock_server
        with patch("smtplib.SMTP", return_value=mock_smtp_cm):
            adapter.send_welcome("user@test.com", "TR")
    mock_server.starttls.assert_not_called()


def test_smtp_adapter_returns_false_on_exception_not_raises():
    with patch("src.adapters.notifications.email_adapter.settings") as mock_settings:
        mock_settings.smtp_host = "smtp.gmail.com"
        mock_settings.smtp_port = 587
        mock_settings.smtp_user = "me@gmail.com"
        mock_settings.smtp_password = "bad"
        mock_settings.smtp_from = ""
        mock_settings.email_from = "NexStream <no-reply@test.com>"
        mock_settings.smtp_starttls = True
        adapter = SmtpEmailAdapter()
        with patch("smtplib.SMTP", side_effect=Exception("auth failed")):
            result = adapter.send_welcome("user@test.com", "TR")
    assert result is False


def test_get_email_adapter_auto_prefers_smtp_over_resend_when_both_configured():
    with patch("src.adapters.notifications.email_adapter.settings") as mock_settings:
        mock_settings.email_provider = "auto"
        mock_settings.smtp_user = "me@gmail.com"
        mock_settings.smtp_password = "app-password"
        mock_settings.resend_api_key = "re_also_set"
        adapter = get_email_adapter()
    assert isinstance(adapter, SmtpEmailAdapter)


def test_get_email_adapter_explicit_provider_forces_console():
    with patch("src.adapters.notifications.email_adapter.settings") as mock_settings:
        mock_settings.email_provider = "console"
        mock_settings.smtp_user = "me@gmail.com"
        mock_settings.smtp_password = "app-password"
        mock_settings.resend_api_key = "re_set"
        adapter = get_email_adapter()
    assert isinstance(adapter, ConsoleEmailAdapter)


def test_get_email_adapter_explicit_provider_forces_smtp():
    with patch("src.adapters.notifications.email_adapter.settings") as mock_settings:
        mock_settings.email_provider = "smtp"
        mock_settings.smtp_user = ""
        mock_settings.smtp_password = ""
        adapter = get_email_adapter()
    assert isinstance(adapter, SmtpEmailAdapter)
