"""Cache kompozisyon noktası: REDIS_URL doluysa Redis, boşsa NullCache."""

from src.domain.ports.cache_port import CachePort
from src.adapters.cache.null_cache_adapter import NullCacheAdapter
from src.infrastructure.config.settings import settings


def build_cache() -> CachePort:
    if settings.redis_url:
        from src.adapters.cache.redis_adapter import RedisAdapter
        return RedisAdapter(settings.redis_url)
    return NullCacheAdapter()
