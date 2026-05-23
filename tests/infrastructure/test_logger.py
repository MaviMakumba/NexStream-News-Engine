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
