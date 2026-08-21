"""YahooFinanceMarketAdapter testleri — gerçek HTTP çağrısı YOK,
requests.get mock'lanır (proje kuralı, bkz. CLAUDE.md)."""

from unittest.mock import MagicMock, patch

import pytest

from src.adapters.market.yahoo_finance_adapter import YahooFinanceMarketAdapter
from src.domain.ports.market_data_port import MarketDataError


def _chart_response(price: float, previous: float) -> MagicMock:
    resp = MagicMock()
    resp.raise_for_status.return_value = None
    resp.json.return_value = {
        "chart": {"result": [{"meta": {"regularMarketPrice": price, "previousClose": previous}}]}
    }
    return resp


_QUOTES = {
    "XU100.IS": (10000.0, 9900.0),
    "USDTRY=X": (34.0, 33.5),
    "EURTRY=X": (37.0, 36.8),
    "GC=F": (2500.0, 2480.0),
}


def _fake_get(url, headers=None, timeout=None, params=None):
    symbol = url.rsplit("/", 1)[-1]
    price, previous = _QUOTES[symbol]
    return _chart_response(price, previous)


def test_get_snapshot_maps_all_four_symbols():
    adapter = YahooFinanceMarketAdapter()
    with patch("src.adapters.market.yahoo_finance_adapter.requests.get", side_effect=_fake_get):
        snapshot = adapter.get_snapshot()

    assert snapshot.bist100.value == 10000.0
    assert round(snapshot.bist100.change_pct, 4) == round((10000.0 - 9900.0) / 9900.0 * 100, 4)
    assert snapshot.usd_try.value == 34.0
    assert snapshot.eur_try.value == 37.0
    assert snapshot.stale is False


def test_get_snapshot_derives_gold_gram_try_from_ounce_and_usdtry():
    quotes = dict(_QUOTES)
    quotes["GC=F"] = (2500.0, 2500.0)
    quotes["USDTRY=X"] = (34.0, 34.0)

    def fake_get(url, headers=None, timeout=None, params=None):
        symbol = url.rsplit("/", 1)[-1]
        price, previous = quotes[symbol]
        return _chart_response(price, previous)

    adapter = YahooFinanceMarketAdapter()
    with patch("src.adapters.market.yahoo_finance_adapter.requests.get", side_effect=fake_get):
        snapshot = adapter.get_snapshot()

    expected_gram_try = (2500.0 / 31.1034768) * 34.0
    assert round(snapshot.gold_gram_try.value, 2) == round(expected_gram_try, 2)
    assert snapshot.gold_gram_try.change_pct == 0.0  # fiyat == önceki kapanış


def test_get_snapshot_raises_market_data_error_on_http_failure():
    adapter = YahooFinanceMarketAdapter()
    with patch("src.adapters.market.yahoo_finance_adapter.requests.get",
               side_effect=ConnectionError("boom")):
        with pytest.raises(MarketDataError):
            adapter.get_snapshot()


def test_get_snapshot_raises_market_data_error_on_invalid_symbol_response():
    """Yahoo'nun geçersiz/delisted bir sembol için GERÇEKTEN döndüğü şekli
    mock'lar — bu hipotetik bir "bozuk JSON" değil, XAUUSD=X'in canlıda
    döndürdüğü tam yanıt (bkz. Fix 1). result None olunca [0] indexlemesi
    TypeError fırlatır — get_snapshot bunu yutup MarketDataError'a çevirmeli,
    çıplak TypeError sızdırmamalı."""
    invalid_resp = MagicMock()
    invalid_resp.raise_for_status.return_value = None
    invalid_resp.json.return_value = {
        "chart": {
            "result": None,
            "error": {"code": "Not Found", "description": "No data found, symbol may be delisted"},
        }
    }

    def fake_get(url, headers=None, timeout=None, params=None):
        symbol = url.rsplit("/", 1)[-1]
        if symbol == "GC=F":
            return invalid_resp
        price, previous = _QUOTES[symbol]
        return _chart_response(price, previous)

    adapter = YahooFinanceMarketAdapter()
    with patch("src.adapters.market.yahoo_finance_adapter.requests.get", side_effect=fake_get):
        with pytest.raises(MarketDataError):
            adapter.get_snapshot()
