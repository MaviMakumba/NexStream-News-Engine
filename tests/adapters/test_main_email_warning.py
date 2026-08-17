import logging
from src.adapters.notifications.email_adapter import ConsoleEmailAdapter, ResendEmailAdapter


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
