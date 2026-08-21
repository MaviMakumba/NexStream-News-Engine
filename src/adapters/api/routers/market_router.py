"""Piyasa verisi — GET /market/ticker (BİST100/USD/EUR/gram altın).

Public, auth gerektirmez (haber okuma gibi şeffaf) — kendi cache'i olduğu
için ayrı bir rate limit de yok. CachePort ile iki katmanlı tutulur:
- "market:snapshot" — TTL'li (settings.market_cache_ttl_seconds), taze veri.
- "market:snapshot:last_good" — 24 saat TTL'li, Yahoo uzun süre kesilse bile
  gösterilecek bir son iyi değer kalsın diye ("ölü besleme çökertmez"
  deseninin piyasa verisi karşılığı, bkz. RSS scraper'lar).

Yahoo hatası alınıp last_good'a düşüldüğünde, stale işaretli değer KISA bir
TTL ile (_NEGATIVE_CACHE_TTL_SECONDS) fresh anahtara da yazılır — yoksa
kesinti boyunca her istek fresh cache boş kaldığı için 4 Yahoo çağrısını
(her biri timeout'a kadar) tekrar tetikler ("request stampede").
"""

import logging

from fastapi import APIRouter, Depends, Response

from src.dependencies import get_cache, get_market_data_adapter
from src.domain.ports.cache_port import CachePort
from src.domain.ports.market_data_port import MarketDataError, MarketDataPort
from src.domain.schemas.market_schema import MarketSnapshot
from src.infrastructure.config.settings import settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/market", tags=["Market"])

_CACHE_KEY = "market:snapshot"
_LAST_GOOD_KEY = "market:snapshot:last_good"
_LAST_GOOD_TTL_SECONDS = 24 * 60 * 60
# Yahoo kesintisi sırasında stale değeri fresh anahtara da kısa süreliğine
# yazar — yoksa her istek fresh cache boş kaldığı için 4 Yahoo çağrısını
# (her biri timeout'a kadar) tekrar tetikler ("request stampede").
_NEGATIVE_CACHE_TTL_SECONDS = 60


@router.get("/ticker", response_model=MarketSnapshot)
def get_market_ticker(
    cache: CachePort = Depends(get_cache),
    market: MarketDataPort = Depends(get_market_data_adapter),
):
    cached = cache.get(_CACHE_KEY)
    if cached is not None:
        return MarketSnapshot.model_validate(cached)

    try:
        snapshot = market.get_snapshot()
        payload = snapshot.model_dump(mode="json")
        cache.set(_CACHE_KEY, payload, ttl_seconds=settings.market_cache_ttl_seconds)
        cache.set(_LAST_GOOD_KEY, payload, ttl_seconds=_LAST_GOOD_TTL_SECONDS)
        return snapshot
    except MarketDataError as e:
        logger.warning("Piyasa verisi çekilemedi, son iyi değere düşülüyor: %s", e)
        last_good = cache.get(_LAST_GOOD_KEY)
        if last_good is None:
            return Response(status_code=204)
        stale_payload = {**last_good, "stale": True}
        cache.set(_CACHE_KEY, stale_payload, ttl_seconds=_NEGATIVE_CACHE_TTL_SECONDS)
        return MarketSnapshot.model_validate(stale_payload)
