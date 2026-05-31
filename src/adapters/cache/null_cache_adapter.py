from typing import Any, Optional
from src.domain.ports.cache_port import CachePort


class NullCacheAdapter(CachePort):
    """No-op cache — always misses. Used when Redis is not configured."""

    def get(self, key: str) -> Optional[Any]:
        return None

    def set(self, key: str, value: Any, ttl_seconds: int = 60) -> None:
        pass

    def delete(self, key: str) -> None:
        pass
