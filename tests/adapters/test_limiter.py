"""slowapi limiter storage seçimi — 19 Ağu 2026 güvenlik denetiminde bulundu:
prod `uvicorn --workers 2` ile çalışıyor ama limiter'ın storage_uri'si hiç
set edilmemişti → slowapi'nin varsayılan in-memory sayacı her worker'da AYRI
tutulur, yani kodda "15/minute" yazsa da canlıda fiilen ~2x'e kadar gevşiyordu
(gerçek istekle doğrulandı: art arda 18 login denemesi hiç 429 almadı).
REDIS_URL zaten prod'da dolu (cache için) — limiter'ın da onu paylaşması
worker'lar arası tutarlı bir sayaç sağlar.
"""

from src.adapters.api.limiter import _limiter_storage_uri


def test_limiter_storage_uri_uses_redis_when_configured():
    assert _limiter_storage_uri("redis://redis:6379/0") == "redis://redis:6379/0"


def test_limiter_storage_uri_falls_back_to_in_memory_when_redis_url_empty():
    """REDIS_URL boşsa (dev/tek-worker) None döner — slowapi bunu in-memory'e
    yorumlar, mevcut dev davranışı bozulmaz."""
    assert _limiter_storage_uri("") is None
