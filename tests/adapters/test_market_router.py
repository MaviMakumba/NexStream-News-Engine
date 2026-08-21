"""GET /market/ticker testleri — cache hit/miss/stale/204 yolları.
CachePort ve MarketDataPort mock'lanır, gerçek Yahoo çağrısı YOK."""

from datetime import datetime, timezone
from unittest.mock import MagicMock

from src.adapters.api.routers.market_router import _LAST_GOOD_TTL_SECONDS
from src.domain.ports.market_data_port import MarketDataError
from src.domain.schemas.market_schema import MarketQuote, MarketSnapshot
from src.infrastructure.config.settings import settings


def _snapshot() -> MarketSnapshot:
    q = MarketQuote(value=100.0, change_pct=1.0)
    return MarketSnapshot(
        bist100=q, usd_try=q, eur_try=q, gold_gram_try=q,
        as_of=datetime(2026, 8, 21, 12, 0, tzinfo=timezone.utc),
    )


def _override(app_client, cache, market):
    from src.dependencies import get_cache, get_market_data_adapter
    app_client.app.dependency_overrides[get_cache] = lambda: cache
    app_client.app.dependency_overrides[get_market_data_adapter] = lambda: market


def _clear(app_client):
    app_client.app.dependency_overrides.clear()


def test_ticker_returns_cached_snapshot_without_calling_market(app_client):
    cache = MagicMock()
    cache.get.return_value = _snapshot().model_dump(mode="json")
    market = MagicMock()
    _override(app_client, cache, market)
    try:
        r = app_client.get("/market/ticker")
    finally:
        _clear(app_client)

    assert r.status_code == 200
    assert r.json()["usd_try"]["value"] == 100.0
    market.get_snapshot.assert_not_called()


def test_ticker_fetches_and_caches_on_miss(app_client):
    cache = MagicMock()
    cache.get.return_value = None
    market = MagicMock()
    market.get_snapshot.return_value = _snapshot()
    _override(app_client, cache, market)
    try:
        r = app_client.get("/market/ticker")
    finally:
        _clear(app_client)

    assert r.status_code == 200
    assert r.json()["stale"] is False
    assert cache.set.call_count == 2  # taze anahtar + last_good anahtarı
    # Sadece cagri sayisi degil, HANGI anahtara HANGI TTL ile yazildigini da
    # dogrula — ikisi de ayni anahtara giderse regresyon burada yakalanmali
    # (stale-fallback tasariminin sessizce kirilmasini onlemek icin).
    first_call, second_call = cache.set.call_args_list
    assert first_call.args[0] == "market:snapshot"
    assert first_call.kwargs["ttl_seconds"] == settings.market_cache_ttl_seconds
    assert second_call.args[0] == "market:snapshot:last_good"
    assert second_call.kwargs["ttl_seconds"] == _LAST_GOOD_TTL_SECONDS


def test_ticker_falls_back_to_last_good_on_failure(app_client):
    cache = MagicMock()
    last_good = _snapshot().model_dump(mode="json")
    cache.get.side_effect = lambda key: last_good if key.endswith("last_good") else None
    market = MagicMock()
    market.get_snapshot.side_effect = MarketDataError("boom")
    _override(app_client, cache, market)
    try:
        r = app_client.get("/market/ticker")
    finally:
        _clear(app_client)

    assert r.status_code == 200
    assert r.json()["stale"] is True


def test_ticker_returns_204_when_no_data_ever_fetched(app_client):
    cache = MagicMock()
    cache.get.return_value = None
    market = MagicMock()
    market.get_snapshot.side_effect = MarketDataError("boom")
    _override(app_client, cache, market)
    try:
        r = app_client.get("/market/ticker")
    finally:
        _clear(app_client)

    assert r.status_code == 204
