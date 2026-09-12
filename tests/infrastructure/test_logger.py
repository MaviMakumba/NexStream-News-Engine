import json
import logging
import os
from unittest.mock import patch
from src.infrastructure.config.settings import Settings


def test_json_formatter_produces_valid_json():
    from src.infrastructure.logging.logger import _JSONFormatter
    formatter = _JSONFormatter()
    record = logging.LogRecord(
        name="test.logger",
        level=logging.INFO,
        pathname="",
        lineno=0,
        msg="test message",
        args=(),
        exc_info=None,
    )
    output = formatter.format(record)
    data = json.loads(output)
    assert data["level"] == "INFO"
    assert data["msg"] == "test message"
    assert data["logger"] == "test.logger"
    assert "ts" in data


def test_json_formatter_includes_exception():
    from src.infrastructure.logging.logger import _JSONFormatter
    formatter = _JSONFormatter()
    try:
        raise ValueError("test error")
    except ValueError:
        import sys
        exc_info = sys.exc_info()

    record = logging.LogRecord(
        name="test",
        level=logging.ERROR,
        pathname="",
        lineno=0,
        msg="error occurred",
        args=(),
        exc_info=exc_info,
    )
    output = formatter.format(record)
    data = json.loads(output)
    assert "exc" in data
    assert "ValueError" in data["exc"]


def test_text_formatter_contains_message():
    from src.infrastructure.logging.logger import _TextFormatter
    formatter = _TextFormatter()
    record = logging.LogRecord(
        name="test",
        level=logging.WARNING,
        pathname="",
        lineno=0,
        msg="warning msg",
        args=(),
        exc_info=None,
    )
    output = formatter.format(record)
    assert "warning msg" in output
    assert "WARNING" in output


def test_setup_logging_json():
    test_settings = Settings(_env_file=None)
    test_settings.log_format = "json"
    test_settings.log_level = "INFO"

    with patch("src.infrastructure.logging.logger.settings", test_settings):
        from src.infrastructure.logging.logger import setup_logging, _JSONFormatter
        setup_logging()
        root = logging.getLogger()
        assert root.handlers
        assert isinstance(root.handlers[0].formatter, _JSONFormatter)


def test_setup_logging_text():
    test_settings = Settings(_env_file=None)
    test_settings.log_format = "text"
    test_settings.log_level = "DEBUG"

    with patch("src.infrastructure.logging.logger.settings", test_settings):
        from src.infrastructure.logging.logger import setup_logging, _TextFormatter
        setup_logging()
        root = logging.getLogger()
        assert isinstance(root.handlers[0].formatter, _TextFormatter)


def test_json_formatter_includes_request_id_when_set():
    """13 Eyl 2026: uçtan uca request_id — nginx log ↔ app log ↔ security_events."""
    import json, logging
    from src.infrastructure.logging.logger import _JSONFormatter
    from src.adapters.api.request_context import bind_request_id

    token = bind_request_id("abc123")
    try:
        record = logging.LogRecord("t", logging.INFO, "f.py", 1, "hello", None, None)
        entry = json.loads(_JSONFormatter().format(record))
    finally:
        bind_request_id(None, token)
    assert entry["request_id"] == "abc123"


def test_json_formatter_omits_request_id_outside_requests():
    import json, logging
    from src.infrastructure.logging.logger import _JSONFormatter
    record = logging.LogRecord("t", logging.INFO, "f.py", 1, "hello", None, None)
    assert "request_id" not in json.loads(_JSONFormatter().format(record))
