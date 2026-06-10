"""Redis cache adapter'ı — CachePort'un Redis implementasyonu.

Bağlantı hatası isteği düşürmez: get None döner, set/delete sessizce loglar.
"""

import json
import logging
from typing import Any, Optional

import redis

from src.domain.ports.cache_port import CachePort

logger = logging.getLogger(__name__)


class RedisAdapter(CachePort):
    def __init__(self, url: str):
        self._client = redis.from_url(url, decode_responses=True, socket_connect_timeout=3)

    def get(self, key: str) -> Optional[Any]:
        try:
            raw = self._client.get(key)
            return json.loads(raw) if raw is not None else None
        except Exception as e:
            logger.warning("Redis get hatası (%s): %s", key, e)
            return None

    def set(self, key: str, value: Any, ttl_seconds: int = 60) -> None:
        try:
            self._client.setex(key, ttl_seconds, json.dumps(value))
        except Exception as e:
            logger.warning("Redis set hatası (%s): %s", key, e)

    def delete(self, key: str) -> None:
        try:
            self._client.delete(key)
        except Exception as e:
            logger.warning("Redis delete hatası (%s): %s", key, e)
