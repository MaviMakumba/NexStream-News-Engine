"""MarketSnapshot'un CachePort üzerinden JSON round-trip'i güvenli mi?

RedisAdapter.set() değeri json.dumps ile, get() json.loads ile taşıyor —
model_dump(mode="json") kullanılmazsa datetime alanı json.dumps'ta patlar.
Bu test o sözleşmeyi kilitler.
"""

import json
from datetime import datetime, timezone

from src.domain.schemas.market_schema import MarketSnapshot, MarketQuote


def _make_snapshot() -> MarketSnapshot:
    q = MarketQuote(value=100.0, change_pct=1.5)
    return MarketSnapshot(
        bist100=q, usd_try=q, eur_try=q, gold_gram_try=q,
        as_of=datetime(2026, 8, 21, 12, 0, tzinfo=timezone.utc),
    )


def test_market_snapshot_json_roundtrip_survives_cache_serialization():
    snapshot = _make_snapshot()
    payload = snapshot.model_dump(mode="json")

    raw = json.dumps(payload)            # RedisAdapter.set()'in yaptığı
    restored_dict = json.loads(raw)      # RedisAdapter.get()'in yaptığı
    restored = MarketSnapshot.model_validate(restored_dict)

    assert restored == snapshot


def test_market_snapshot_default_stale_is_false():
    assert _make_snapshot().stale is False
