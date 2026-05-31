import pytest
from unittest.mock import patch, MagicMock
from src.adapters.cache.null_cache_adapter import NullCacheAdapter
from src.adapters.cache.redis_adapter import RedisAdapter
from src.adapters.cache.factory import build_cache


# ── NullCacheAdapter ──────────────────────────────────────────────────────────

def test_null_cache_get_always_returns_none():
    cache = NullCacheAdapter()
    assert cache.get("any_key") is None


def test_null_cache_set_does_nothing():
    cache = NullCacheAdapter()
    cache.set("key", {"data": 42}, ttl_seconds=60)
    assert cache.get("key") is None


def test_null_cache_delete_does_nothing():
    cache = NullCacheAdapter()
    cache.delete("nonexistent")  # should not raise


# ── RedisAdapter ──────────────────────────────────────────────────────────────

def test_redis_adapter_set_and_get():
    mock_client = MagicMock()
    mock_client.get.return_value = '{"value": 42}'

    with patch("src.adapters.cache.redis_adapter.redis") as mock_redis:
        mock_redis.from_url.return_value = mock_client
        adapter = RedisAdapter("redis://localhost:6379/0")

    adapter._client = mock_client
    result = adapter.get("test_key")
    assert result == {"value": 42}


def test_redis_adapter_miss_returns_none():
    mock_client = MagicMock()
    mock_client.get.return_value = None

    with patch("src.adapters.cache.redis_adapter.redis") as mock_redis:
        mock_redis.from_url.return_value = mock_client
        adapter = RedisAdapter("redis://localhost:6379/0")

    adapter._client = mock_client
    assert adapter.get("missing_key") is None


def test_redis_adapter_set_uses_setex():
    mock_client = MagicMock()
    with patch("src.adapters.cache.redis_adapter.redis") as mock_redis:
        mock_redis.from_url.return_value = mock_client
        adapter = RedisAdapter("redis://localhost:6379/0")

    adapter._client = mock_client
    adapter.set("my_key", {"x": 1}, ttl_seconds=300)
    mock_client.setex.assert_called_once()
    args = mock_client.setex.call_args[0]
    assert args[0] == "my_key"
    assert args[1] == 300


def test_redis_adapter_connection_error_returns_none():
    mock_client = MagicMock()
    mock_client.get.side_effect = Exception("Connection refused")

    with patch("src.adapters.cache.redis_adapter.redis") as mock_redis:
        mock_redis.from_url.return_value = mock_client
        adapter = RedisAdapter("redis://localhost:6379/0")

    adapter._client = mock_client
    result = adapter.get("key")
    assert result is None


# ── build_cache factory ───────────────────────────────────────────────────────

def test_build_cache_returns_null_when_no_redis_url():
    with patch("src.adapters.cache.factory.settings") as mock_settings:
        mock_settings.redis_url = ""
        cache = build_cache()
    assert isinstance(cache, NullCacheAdapter)


def test_build_cache_returns_redis_when_url_set():
    with patch("src.adapters.cache.factory.settings") as mock_settings:
        mock_settings.redis_url = "redis://localhost:6379/0"
        with patch("src.adapters.cache.redis_adapter.RedisAdapter") as MockRedis:
            MockRedis.return_value = MagicMock()
            cache = build_cache()
    assert not isinstance(cache, NullCacheAdapter)
