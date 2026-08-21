"""Piyasa ticker'ı API yanıt şeması (Pydantic) — GET /market/ticker.

CachePort.set() değeri json.dumps ile serialize ediyor (bkz. RedisAdapter) —
bu yüzden cache'e yazmadan önce MarketSnapshot.model_dump(mode="json")
(datetime → ISO string) kullanılmalı, ham .model_dump() DEĞİL.
"""

from datetime import datetime

from pydantic import BaseModel


class MarketQuote(BaseModel):
    value: float
    change_pct: float


class MarketSnapshot(BaseModel):
    bist100: MarketQuote
    usd_try: MarketQuote
    eur_try: MarketQuote
    gold_gram_try: MarketQuote
    as_of: datetime
    stale: bool = False
