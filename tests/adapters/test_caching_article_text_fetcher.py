from src.adapters.api.metrics import article_fetch_total
from src.adapters.scrapers.caching_article_text_fetcher import CachingArticleTextFetcher
from src.domain.ports.article_text_port import ArticleTextPort
from src.domain.ports.cache_port import CachePort


class FakeCache(CachePort):
    def __init__(self):
        self.store, self.ttls = {}, {}

    def get(self, key):
        return self.store.get(key)

    def set(self, key, value, ttl_seconds=60):
        self.store[key] = value
        self.ttls[key] = ttl_seconds

    def delete(self, key):
        self.store.pop(key, None)


class CountingFetcher(ArticleTextPort):
    def __init__(self, text):
        self.text, self.calls = text, 0

    def fetch(self, url):
        self.calls += 1
        return self.text


def _hits():
    return article_fetch_total.labels(result="hit")._value.get()


def test_success_is_cached_with_success_ttl_and_second_call_skips_inner():
    cache, inner = FakeCache(), CountingFetcher("Makale metni")
    f = CachingArticleTextFetcher(inner, cache, ttl_seconds=3600, failure_ttl_seconds=300)
    before = _hits()
    assert f.fetch("https://a.example/1") == "Makale metni"
    assert f.fetch("https://a.example/1") == "Makale metni"
    assert inner.calls == 1
    assert _hits() == before + 1
    assert list(cache.ttls.values()) == [3600]


def test_failure_is_negative_cached_with_short_ttl():
    cache, inner = FakeCache(), CountingFetcher(None)
    f = CachingArticleTextFetcher(inner, cache, ttl_seconds=3600, failure_ttl_seconds=300)
    assert f.fetch("https://a.example/1") is None
    assert f.fetch("https://a.example/1") is None
    assert inner.calls == 1
    assert list(cache.ttls.values()) == [300]


def test_different_urls_use_different_keys():
    cache, inner = FakeCache(), CountingFetcher("x")
    f = CachingArticleTextFetcher(inner, cache, ttl_seconds=10, failure_ttl_seconds=5)
    f.fetch("https://a.example/1")
    f.fetch("https://a.example/2")
    assert inner.calls == 2 and len(cache.store) == 2
    assert all(k.startswith("arttext:") and "a.example" not in k for k in cache.store)
