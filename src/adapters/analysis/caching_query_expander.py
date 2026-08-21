"""src/adapters/analysis/caching_query_expander.py

QueryExpansionPort'u CachePort ile saran bir decorator — cache hit'te
alttaki (gerçek Groq çağrısı yapan) expander'a hiç gitmez. Dolu sonuç 30
gün, boş sonuç 1 saat cache'lenir (geçici bir Groq arızasını kalıcı "hiç
genişletme yok" damgası yapmamak için). Cache okuma/yazma hatası zaten
CachePort implementasyonlarının (RedisAdapter, NullCacheAdapter) kendi
sorumluluğu — burada ekstra try/except gerekmiyor.
"""

from typing import List

from src.domain.ports.query_expansion_port import QueryExpansionPort
from src.domain.ports.cache_port import CachePort
from src.adapters.api.metrics import query_expansion_total

_TTL_HIT_SECONDS = 30 * 24 * 60 * 60   # 30 gün
_TTL_EMPTY_SECONDS = 60 * 60           # 1 saat


class CachingQueryExpander(QueryExpansionPort):
    def __init__(self, inner: QueryExpansionPort, cache: CachePort):
        self.inner = inner
        self.cache = cache

    def expand(self, query: str) -> List[str]:
        key = f"qexp:{query.strip().lower()}"
        cached = self.cache.get(key)
        if cached is not None:
            query_expansion_total.labels(result="hit").inc()
            return cached
        # Cache miss'te BURADA etiket basılmaz: bu decorator herhangi bir
        # QueryExpansionPort'u sarabilir, sonucun "expanded/empty/error"
        # ayrımını sadece alttaki somut adapter bilir — o kendi sonucunu
        # kendisi raporlar (tek doğruluk noktası, çift sayım yok).
        terms = self.inner.expand(query)
        ttl = _TTL_HIT_SECONDS if terms else _TTL_EMPTY_SECONDS
        self.cache.set(key, terms, ttl_seconds=ttl)
        return terms
