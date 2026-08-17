import logging
from unittest.mock import patch
from src.adapters.notifications.email_adapter import ConsoleEmailAdapter, ResendEmailAdapter, SmtpEmailAdapter


def test_warn_if_email_disabled_logs_error_in_production(app_client, caplog):
    """`app_client` reloads src.main with all I/O mocked (see conftest.py) — reuse
    that already-imported, safely-patched module instead of a bare `import src.main`."""
    import src.main
    with caplog.at_level(logging.ERROR, logger="src.main"):
        src.main.warn_if_email_disabled("production", ConsoleEmailAdapter())
    assert any("mail" in r.message.lower() or "console" in r.message.lower() for r in caplog.records)


def test_warn_if_email_disabled_silent_in_development(app_client, caplog):
    import src.main
    with caplog.at_level(logging.ERROR, logger="src.main"):
        src.main.warn_if_email_disabled("development", ConsoleEmailAdapter())
    assert caplog.records == []


def test_warn_if_email_disabled_silent_when_adapter_is_not_console(app_client, caplog):
    import src.main
    with caplog.at_level(logging.ERROR, logger="src.main"):
        src.main.warn_if_email_disabled("production", ResendEmailAdapter())
    assert caplog.records == []


def test_warn_if_email_disabled_logs_error_when_smtp_credentials_missing(app_client, caplog):
    """EMAIL_PROVIDER=smtp seçilip SMTP_USER/SMTP_PASSWORD boş bırakılırsa
    (adapter yine SmtpEmailAdapter döner) production'da artık Console'a düşüş
    kadar açık şekilde loglanmalı (Finding 3)."""
    import src.main
    with patch("src.adapters.notifications.email_adapter.settings") as mock_settings:
        mock_settings.smtp_host = "smtp.gmail.com"
        mock_settings.smtp_port = 587
        mock_settings.smtp_user = ""
        mock_settings.smtp_password = ""
        mock_settings.smtp_from = ""
        mock_settings.email_from = "NexStream <no-reply@test.com>"
        mock_settings.smtp_starttls = True
        adapter = SmtpEmailAdapter()
    with caplog.at_level(logging.ERROR, logger="src.main"):
        src.main.warn_if_email_disabled("production", adapter)
    assert any("smtp" in r.message.lower() for r in caplog.records)


def test_warn_if_email_disabled_silent_when_smtp_credentials_present(app_client, caplog):
    import src.main
    with patch("src.adapters.notifications.email_adapter.settings") as mock_settings:
        mock_settings.smtp_host = "smtp.gmail.com"
        mock_settings.smtp_port = 587
        mock_settings.smtp_user = "me@gmail.com"
        mock_settings.smtp_password = "app-password"
        mock_settings.smtp_from = ""
        mock_settings.email_from = "NexStream <no-reply@test.com>"
        mock_settings.smtp_starttls = True
        adapter = SmtpEmailAdapter()
    with caplog.at_level(logging.ERROR, logger="src.main"):
        src.main.warn_if_email_disabled("production", adapter)
    assert caplog.records == []
