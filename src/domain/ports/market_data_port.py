"""Piyasa verisi port'u — BİST100/USD/EUR/gram altın anlık değer sözleşmesi.

Tek somut implementasyon: YahooFinanceMarketAdapter (resmi olmayan, key
gerektirmez). Fallback zinciri yok (AnalysisPort'un aksine) — tek kaynak,
başarısızlıkta çağıran taraf (market_router) cache'teki son iyi değere döner.
"""

from abc import ABC, abstractmethod

from src.domain.schemas.market_schema import MarketSnapshot


class MarketDataError(Exception):
    """Piyasa verisi çekilemediğinde fırlatılır (Yahoo Finance erişilemez/format değişti)."""


class MarketDataPort(ABC):
    @abstractmethod
    def get_snapshot(self) -> MarketSnapshot:
        """Güncel BİST100/USD/EUR/gram altın anlık görüntüsünü döner.

        Başarısızlıkta MarketDataError fırlatır — nötr/boş bir sonuç DÖNMEZ
        (AnalysisPort.analyze_text'in aksine; burada anlamlı bir nötr değer
        yok, 0 TL/USD yanıltıcı olurdu). Çağıran taraf (router) cache'e düşer.
        """
        pass
