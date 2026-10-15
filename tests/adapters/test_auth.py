import asyncio
import pytest
from unittest.mock import patch
from fastapi import HTTPException


def test_verify_api_key_missing_raises_401():
    from src.adapters.api.auth import verify_api_key
    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(verify_api_key(x_api_key=None))
    assert exc_info.value.status_code == 401


def test_verify_api_key_wrong_raises_401():
    from src.adapters.api.auth import verify_api_key
    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(verify_api_key(x_api_key="wrong-key"))
    assert exc_info.value.status_code == 401


def test_verify_api_key_correct_passes():
    from src.infrastructure.config.settings import Settings
    test_settings = Settings(_env_file=None)
    test_settings.api_key = "test-secret"

    with patch("src.adapters.api.auth.settings", test_settings):
        from src.adapters.api.auth import verify_api_key
        result = asyncio.run(verify_api_key(x_api_key="test-secret"))
    assert result is None


def test_verify_api_key_empty_string_raises_401():
    from src.adapters.api.auth import verify_api_key
    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(verify_api_key(x_api_key=""))
    assert exc_info.value.status_code == 401


def test_verify_api_key_error_message():
    from src.adapters.api.auth import verify_api_key
    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(verify_api_key(x_api_key=None))
    assert "API key" in exc_info.value.detail


def test_api_key_with_non_ascii_header_is_rejected_not_crashed():
    """X-API-Key başlığına ASCII dışı karakter konursa `compare_digest` TypeError
    atıp 500 üretmemeli, 401 dönmeli (Sentry PYTHON-FASTAPI-19 ile aynı sınıf)."""
    from src.adapters.api.auth import api_key_matches
    assert api_key_matches("çğüş-anahtar") is False
