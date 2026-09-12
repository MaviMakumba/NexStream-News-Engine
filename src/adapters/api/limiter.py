"""slowapi rate limiter singleton'ı — tüm router'lar bu instance'ı paylaşır.

Storage backend (19 Ağu 2026 güvenlik denetiminde bulundu): prod
`uvicorn --workers 2` ile çalışıyor, ama storage_uri hiç set edilmemişti —
slowapi'nin varsayılanı in-memory'dir ve her worker AYRI bir process olduğu
için kendi sayacını tutar. Sonuç: kodda "15/minute" yazsa da istekler iki
worker'a round-robin dağıtıldığı için limit fiilen ~2 katına kadar gevşiyordu
(canlıda art arda 18 login denemesiyle doğrulandı — hiç 429 gelmedi).
REDIS_URL zaten prod'da dolu (cache için, bkz. adapters/cache/factory.py) —
aynı env var'ı paylaşmak worker'lar arası tek bir sayaç sağlar. `redis_url`
boşsa (dev/tek-worker) None döner, slowapi bunu in-memory'e yorumlar — dev
davranışı değişmez. `in_memory_fallback_enabled=True`: Redis kısa süreli
erişilemez olursa istekler 500 ile çökmek yerine in-memory'e düşer (projenin
genel "exception yut, fallback dön" ilkesiyle tutarlı).
"""

from typing import Optional

from slowapi import Limiter
from src.adapters.api.request_context import client_ip

from src.infrastructure.config.settings import settings


def _limiter_storage_uri(redis_url: str) -> Optional[str]:
    """REDIS_URL doluysa onu, boşsa None (slowapi'nin in-memory varsayılanı) döner."""
    return redis_url or None


# key_func (13 Eyl 2026): eskiden slowapi'nin get_remote_address'i —
# request.client.host — kullanılıyordu; uvicorn proxy header'larını kabul
# etmediği için bu prod'da NGINX'in iç IP'siydi, yani TÜM ziyaretçiler tek
# kovada sayılıyordu (bir kötüye kullanan herkesi 429'a düşürebilirdi).
# client_ip nginx'in yazdığı X-Real-IP'yi (Cloudflare düzeltmeli) okur.
limiter = Limiter(
    key_func=client_ip,
    storage_uri=_limiter_storage_uri(settings.redis_url),
    in_memory_fallback_enabled=True,
)
