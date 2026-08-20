"""tests/adapters/test_query_expander_factory.py"""
from unittest.mock import MagicMock
from src.adapters.analysis import factory
from src.adapters.analysis.caching_query_expander import CachingQueryExpander


def test_build_query_expander_returns_none_when_disabled(monkeypatch):
    monkeypatch.setattr(factory.settings, "search_query_expansion_enabled", False)
    assert factory.build_query_expander(cache=MagicMock()) is None


def test_build_query_expander_returns_caching_decorator_when_enabled(monkeypatch):
    monkeypatch.setattr(factory.settings, "search_query_expansion_enabled", True)
    result = factory.build_query_expander(cache=MagicMock())
    assert isinstance(result, CachingQueryExpander)
