"""Yahoo Finance adapter'ı — MarketDataPort'un tek somut implementasyonu.

Resmi bir API DEĞİL (`/v8/finance/chart/{symbol}`, key gerektirmez) — RSS
scraper'larla aynı risk kategorisi: format/erişim habersiz değişebilir,
sessizce MarketDataError fırlatır (worker/app çökmez, router son iyi değere
düşer). User-Agent spoofing gerektirir — varsayılan `requests` UA'sı 403
alabilir.

`/v7/finance/quote` (batch, tek istek) KULLANILMADI — 2023'ten beri bir
"crumb" cookie-exchange dansı gerektiriyor, kırılgan. Bunun yerine 4 sembol
için 4 ayrı `/v8/finance/chart/{symbol}` isteği atılır.
"""

import logging
from datetime import datetime, timezone

import requests

from src.domain.ports.market_data_port import MarketDataError, MarketDataPort
from src.domain.schemas.market_schema import MarketQuote, MarketSnapshot

logger = logging.getLogger(__name__)

_TROY_OUNCE_GRAMS = 31.1034768
_SYMBOL_BIST100 = "XU100.IS"
_SYMBOL_USDTRY = "USDTRY=X"
_SYMBOL_EURTRY = "EURTRY=X"
_SYMBOL_GOLD_OZ = "GC=F"  # COMEX altın vadeli işlemi (USD/oz) — "XAUUSD=X" Yahoo'da
# geçersiz sembol (404/Not Found döner, gerçek canlıda doğrulandı); GC=F spot'a
# yakın bir yaklaşıklık, göz-atma amaçlı ticker için yeterli
_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    )
}


def _quote(price: float, previous: float) -> MarketQuote:
    change_pct = ((price - previous) / previous) * 100 if previous else 0.0
    return MarketQuote(value=round(price, 4), change_pct=round(change_pct, 4))


class YahooFinanceMarketAdapter(MarketDataPort):
    def __init__(self):
        self.base_url = "https://query1.finance.yahoo.com/v8/finance/chart"

    def get_snapshot(self) -> MarketSnapshot:
        try:
            bist_price, bist_prev = self._fetch(_SYMBOL_BIST100)
            usd_price, usd_prev = self._fetch(_SYMBOL_USDTRY)
            eur_price, eur_prev = self._fetch(_SYMBOL_EURTRY)
            gold_price, gold_prev = self._fetch(_SYMBOL_GOLD_OZ)
        except Exception as e:
            logger.error("Yahoo Finance piyasa verisi çekilemedi: %s", e)
            raise MarketDataError("Yahoo Finance erişilemedi") from e

        gram_try = (gold_price / _TROY_OUNCE_GRAMS) * usd_price
        gram_try_prev = (gold_prev / _TROY_OUNCE_GRAMS) * usd_prev

        return MarketSnapshot(
            bist100=_quote(bist_price, bist_prev),
            usd_try=_quote(usd_price, usd_prev),
            eur_try=_quote(eur_price, eur_prev),
            gold_gram_try=_quote(gram_try, gram_try_prev),
            as_of=datetime.now(timezone.utc),
        )

    def _fetch(self, symbol: str) -> tuple[float, float]:
        """(price, previous_close) döner. Başarısızlıkta exception fırlatır
        (get_snapshot yutup MarketDataError'a çevirir)."""
        url = f"{self.base_url}/{symbol}"
        r = requests.get(url, headers=_HEADERS, timeout=10, params={"interval": "1d", "range": "5d"})
        r.raise_for_status()
        meta = r.json()["chart"]["result"][0]["meta"]
        price = float(meta["regularMarketPrice"])
        previous = float(meta.get("previousClose") or meta["chartPreviousClose"])
        return price, previous
