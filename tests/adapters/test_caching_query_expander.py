"""tests/adapters/test_caching_query_expander.py"""
from src.adapters.analysis.caching_query_expander import CachingQueryExpander


class _FakeCache:
    """CachePort'un basit, hatasız bir sahte implementasyonu."""
    def __init__(self):
        self.store = {}
        self.set_calls = []

    def get(self, key):
        return self.store.get(key)

    def set(self, key, value, ttl_seconds=60):
        self.store[key] = value
        self.set_calls.append((key, value, ttl_seconds))

    def delete(self, key):
        self.store.pop(key, None)


class _FakeExpander:
    def __init__(self, terms):
        self.terms = terms
        self.call_count = 0

    def expand(self, query):
        self.call_count += 1
        return self.terms


def test_expand_returns_cached_value_without_calling_inner():
    cache = _FakeCache()
    cache.store["qexp:istanbul"] = ["Beykoz", "Kadıköy"]
    inner = _FakeExpander(["farklı bir sonuç"])

    result = CachingQueryExpander(inner, cache).expand("istanbul")

    assert result == ["Beykoz", "Kadıköy"]
    assert inner.call_count == 0


def test_expand_calls_inner_and_caches_on_miss():
    cache = _FakeCache()
    inner = _FakeExpander(["Beşiktaş", "Fenerbahçe"])

    result = CachingQueryExpander(inner, cache).expand("futbol")

    assert result == ["Beşiktaş", "Fenerbahçe"]
    assert inner.call_count == 1
    assert cache.store["qexp:futbol"] == ["Beşiktaş", "Fenerbahçe"]


def test_expand_normalizes_cache_key_case_and_whitespace():
    cache = _FakeCache()
    inner = _FakeExpander(["x"])

    CachingQueryExpander(inner, cache).expand("  İstanbul  ")

    assert "qexp:i̇stanbul" in cache.store or "qexp:istanbul" in cache.store


def test_expand_caches_empty_result_with_short_ttl():
    cache = _FakeCache()
    inner = _FakeExpander([])

    CachingQueryExpander(inner, cache).expand("asdkjf")

    key, value, ttl = cache.set_calls[0]
    assert value == []
    assert ttl == 60 * 60


def test_expand_caches_nonempty_result_with_long_ttl():
    cache = _FakeCache()
    inner = _FakeExpander(["Beykoz"])

    CachingQueryExpander(inner, cache).expand("istanbul")

    key, value, ttl = cache.set_calls[0]
    assert ttl == 30 * 24 * 60 * 60
