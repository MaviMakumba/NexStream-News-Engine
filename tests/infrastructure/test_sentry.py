"""init_sentry() — opsiyonel, fail-open Sentry kurulumu (v2.4)."""

from unittest.mock import patch

import sentry_sdk

from src.infrastructure.observability.sentry import init_sentry


def test_init_sentry_noop_when_dsn_empty():
    with patch("src.infrastructure.observability.sentry.settings") as ms:
        ms.sentry_dsn = ""
        with patch.object(sentry_sdk, "init") as mock_init:
            init_sentry("app")
    mock_init.assert_not_called()


def test_init_sentry_calls_sdk_init_when_dsn_configured():
    with patch("src.infrastructure.observability.sentry.settings") as ms:
        ms.sentry_dsn = "https://fake@sentry.example.com/1"
        ms.environment = "production"
        ms.sentry_traces_sample_rate = 0.05
        with patch.object(sentry_sdk, "init") as mock_init:
            init_sentry("worker")
    mock_init.assert_called_once_with(
        dsn="https://fake@sentry.example.com/1",
        environment="production",
        server_name="worker",
        traces_sample_rate=0.05,
    )


def test_init_sentry_swallows_sdk_init_errors():
    """Sentry kurulumu patlarsa uygulama açılışını ENGELLEMEMELİ."""
    with patch("src.infrastructure.observability.sentry.settings") as ms:
        ms.sentry_dsn = "https://fake@sentry.example.com/1"
        with patch.object(sentry_sdk, "init", side_effect=Exception("bağlantı hatası")):
            init_sentry("app")  # exception fırlatmamalı
