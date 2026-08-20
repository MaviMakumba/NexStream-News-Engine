"""tests/adapters/test_query_expander_factory.py"""
from unittest.mock import MagicMock
from src.adapters.analysis import factory
from src.adapters.analysis.caching_query_expander import CachingQueryExpander


def test_build_query_expander_returns_none_when_disabled(monkeypatch):
    monkeypatch.setattr(factory.settings, "search_query_expansion_enabled", False)
    monkeypatch.setattr(factory.settings, "redis_url", "redis://localhost:6379/0")
    assert factory.build_query_expander(cache=MagicMock()) is None


def test_build_query_expander_returns_caching_decorator_when_enabled(monkeypatch):
    monkeypatch.setattr(factory.settings, "search_query_expansion_enabled", True)
    monkeypatch.setattr(factory.settings, "redis_url", "redis://localhost:6379/0")
    result = factory.build_query_expander(cache=MagicMock())
    assert isinstance(result, CachingQueryExpander)


def test_build_query_expander_returns_none_without_configured_cache(monkeypatch):
    """REDIS_URL boşsa `build_cache()` no-op NullCacheAdapter döner —
    CachingQueryExpander hiçbir şey cache'lemez ve public /search'teki HER
    benzersiz sorgu doğrudan Groq'a gider (analiz hattıyla PAYLAŞILAN kota).
    Bu yüzden genişletme cache olmadan komple kapatılır."""
    monkeypatch.setattr(factory.settings, "search_query_expansion_enabled", True)
    monkeypatch.setattr(factory.settings, "redis_url", "")
    assert factory.build_query_expander(cache=MagicMock()) is None


def test_build_query_expander_warns_only_once_without_cache(monkeypatch, caplog):
    """Fabrika istek başına çağrılıyor — uyarı log'u her istekte tekrarlanmamalı."""
    monkeypatch.setattr(factory.settings, "search_query_expansion_enabled", True)
    monkeypatch.setattr(factory.settings, "redis_url", "")
    monkeypatch.setattr(factory, "_no_cache_warning_logged", False)

    with caplog.at_level("WARNING", logger=factory.logger.name):
        factory.build_query_expander(cache=MagicMock())
        factory.build_query_expander(cache=MagicMock())

    warnings = [r for r in caplog.records if r.levelname == "WARNING"]
    assert len(warnings) == 1
    assert "REDIS_URL" in warnings[0].getMessage()
