"""ArticleTextPort'u CachePort ile saran decorator (CachingQueryExpander ile aynı desen).

Telif kararı: tam metin DB'ye yazılmaz; yalnız bu kısa TTL'li cache'te yaşar. Başarısızlık da
(kısa TTL ile) cache'lenir ki bizi engelleyen bir kaynak her soruda yeniden denenmesin.
`hit` metriği burada basılır; fetched/failed/blocked/too_short sonucunu alttaki somut çekici
kendisi raporlar (tek doğruluk noktası, çift sayım yok).
"""

import hashlib
from typing import Optional

from src.adapters.api.metrics import article_fetch_total
from src.domain.ports.article_text_port import ArticleTextPort
from src.domain.ports.cache_port import CachePort

_FAILURE_SENTINEL = ""


class CachingArticleTextFetcher(ArticleTextPort):
    def __init__(self, inner: ArticleTextPort, cache: CachePort, ttl_seconds: int, failure_ttl_seconds: int):
        self._inner = inner
        self._cache = cache
        self._ttl = ttl_seconds
        self._failure_ttl = failure_ttl_seconds

    def fetch(self, url: str) -> Optional[str]:
        key = "arttext:" + hashlib.sha1(url.encode("utf-8")).hexdigest()
        cached = self._cache.get(key)
        if cached is not None:
            article_fetch_total.labels(result="hit").inc()
            return cached or None
        text = self._inner.fetch(url)
        if text:
            self._cache.set(key, text, ttl_seconds=self._ttl)
        else:
            self._cache.set(key, _FAILURE_SENTINEL, ttl_seconds=self._failure_ttl)
        return text
