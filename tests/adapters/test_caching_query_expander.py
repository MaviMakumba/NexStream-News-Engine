"""tests/adapters/test_caching_query_expander.py"""
from src.adapters.analysis.caching_query_expander import CachingQueryExpander
from src.adapters.api.metrics import query_expansion_total


def _expansion_count(result: str) -> float:
    return query_expansion_total.labels(result=result)._value.get()


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


# ── Metrikler ─────────────────────────────────────────────────────────────────


def test_cache_hit_increments_hit_metric():
    cache = _FakeCache()
    cache.store["qexp:istanbul"] = ["Beykoz"]
    before = _expansion_count("hit")

    CachingQueryExpander(_FakeExpander(["x"]), cache).expand("istanbul")

    assert _expansion_count("hit") == before + 1


def test_cache_miss_leaves_outcome_labels_to_inner_expander():
    """Decorator herhangi bir QueryExpansionPort'u sarabilir — miss'te
    expanded/empty/error ayrımını sadece alttaki somut adapter bilir, bu yüzden
    burada HİÇBİR etiket artmaz (çift sayım olmasın)."""
    cache = _FakeCache()
    before = {r: _expansion_count(r) for r in ("hit", "expanded", "empty", "error")}

    CachingQueryExpander(_FakeExpander(["Beykoz"]), cache).expand("istanbul")

    assert {r: _expansion_count(r) for r in before} == before
