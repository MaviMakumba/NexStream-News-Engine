import os
import pytest
from unittest.mock import patch


def _fresh_settings(**overrides):
    """Yeni bir Settings örneği oluşturur, .env dosyasını atlar."""
    from src.infrastructure.config.settings import Settings
    with patch.dict(os.environ, overrides):
        return Settings(_env_file=None)


def test_settings_loads_defaults():
    s = _fresh_settings()
    assert s.db_host == "localhost"
    assert s.db_port == 5432
    assert s.chroma_host == "localhost"
    assert s.chroma_port == 8001
    assert s.kafka_bootstrap_servers == "kafka:29092"
    assert s.api_key == "dev-key-change-me"
    assert s.log_level == "INFO"
    assert s.log_format == "json"
    assert s.cors_origins == "*"


def test_settings_db_env_override():
    s = _fresh_settings(DB_HOST="mydb", DB_PORT="5433")
    assert s.db_host == "mydb"
    assert s.db_port == 5433


def test_settings_api_key_override():
    s = _fresh_settings(API_KEY="secret-key")
    assert s.api_key == "secret-key"


def test_settings_groq_api_key_override():
    s = _fresh_settings(GROQ_API_KEY="gsk_testkey")
    assert s.groq_api_key == "gsk_testkey"


def test_settings_chroma_override():
    s = _fresh_settings(CHROMA_HOST="chromadb", CHROMA_PORT="8000")
    assert s.chroma_host == "chromadb"
    assert s.chroma_port == 8000


def test_settings_log_format_override():
    s = _fresh_settings(LOG_FORMAT="text", LOG_LEVEL="DEBUG")
    assert s.log_format == "text"
    assert s.log_level == "DEBUG"


def test_settings_scrape_sources_contains_all_17():
    s = _fresh_settings()
    sources = [src.strip() for src in s.scrape_sources.split(",")]
    assert len(sources) == 17
    assert "TRT Haber" in sources
    assert "BBC Technology" in sources
    assert "BBC Sport" in sources
    assert "Anadolu Ajansı" in sources
    assert "TechCrunch" in sources
    assert "The Verge" in sources


def test_settings_huggingface_defaults():
    s = _fresh_settings()
    assert s.huggingface_api_key == ""
    assert s.huggingface_model == "mistralai/Mistral-7B-Instruct-v0.3"


# ── Production güvenlik guard'ı (v1.17 güvenlik denetimi) ──────────────────────

def test_settings_development_ignores_unsafe_defaults():
    """`environment` varsayılanı "development" iken guard hiç çalışmamalı."""
    s = _fresh_settings(API_KEY="dev-key-change-me", BILLING_DEV_MODE="true", CORS_ORIGINS="*")
    assert s.api_key == "dev-key-change-me"


def test_settings_production_rejects_default_api_key():
    with pytest.raises(ValueError, match="API_KEY"):
        _fresh_settings(ENVIRONMENT="production", CORS_ORIGINS="https://example.com")


def test_settings_production_rejects_billing_dev_mode():
    with pytest.raises(ValueError, match="BILLING_DEV_MODE"):
        _fresh_settings(ENVIRONMENT="production", API_KEY="real-key", CORS_ORIGINS="https://example.com",
                         BILLING_DEV_MODE="true")


def test_settings_production_rejects_wildcard_cors():
    with pytest.raises(ValueError, match="CORS_ORIGINS"):
        _fresh_settings(ENVIRONMENT="production", API_KEY="real-key", CORS_ORIGINS="*")


def test_settings_production_rejects_insecure_session_cookie():
    with pytest.raises(ValueError, match="SESSION_COOKIE_SECURE"):
        _fresh_settings(ENVIRONMENT="production", API_KEY="real-key", CORS_ORIGINS="https://example.com",
                         SESSION_COOKIE_SECURE="false")


def test_settings_production_passes_with_safe_config():
    s = _fresh_settings(ENVIRONMENT="production", API_KEY="real-key", CORS_ORIGINS="https://example.com")
    assert s.environment == "production"
