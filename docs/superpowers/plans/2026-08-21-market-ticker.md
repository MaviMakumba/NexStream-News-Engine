# Piyasa Ticker'ı (BİST100/USD/EUR/Gram Altın) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Dashboard'da (Navbar altında) 4 kalemi (BİST100, USD/TRY, EUR/TRY,
gram altın TRY) gösteren, ~60sn'de bir tazelenen, herkese açık bir piyasa
şeridi eklemek.

**Architecture:** Hexagonal — yeni `MarketDataPort` + tek somut adapter
(`YahooFinanceMarketAdapter`, resmi olmayan/key gerektirmeyen Yahoo Finance
chart API'si). Backend `GET /market/ticker` mevcut `CachePort` (Redis/Null)
ile TTL'li cache'ler, başarısızlıkta son iyi değere düşer. Frontend kendi
backend'imizi poll eder, Yahoo'ya hiç doğrudan gitmez.

**Tech Stack:** FastAPI + Pydantic v2 (backend), `requests` (zaten
`requirements.txt`'te), Next.js 14 + React (frontend), mevcut `CachePort`/
`RedisAdapter`/`NullCacheAdapter` (yeni bağımlılık yok).

**Spec:** `docs/superpowers/specs/2026-08-21-market-ticker-design.md`

## Global Constraints

- Cache TTL: `settings.market_cache_ttl_seconds` = 300 (yeni env var, varsayılan 300).
- `GET /market/ticker` **public** — auth/rate-limit yok (kendi cache'i zaten ucuz kılıyor).
- Tek adapter implementasyonu olduğu için **factory dosyası YOK** (spec'ten
  bilinçli sapma — `analysis/factory.py`/`embedder_factory.py` gibi
  factory'ler sadece env-based DALLANMA olduğunda var; burada tek
  implementasyon var, `dependencies.py`'de `get_search_repository()` ile
  aynı doğrudan-singleton deseni kullanılır — YAGNI).
- Gerçek HTTP çağrısı YOK testlerde — hepsi mock (proje kuralı).
- i18n: TÜM kullanıcıya görünen string `lib/i18n.ts::UI[lang]` içinde,
  hardcoded TR/EN metin YOK (CLAUDE.md kuralı).
- Sabit renk YOK — `var(--pos)`/`var(--neg)`/`var(--text)` vb. token kullan.
- Frontend değişikliğinden sonra `npm run build` ile doğrula — frontend
  container ÇALIŞIRKEN host'ta çalıştırma (CLAUDE.md gotcha'sı).

---

### Task 1: Domain katmanı — MarketDataPort + MarketSnapshot şeması

**Files:**
- Create: `src/domain/ports/market_data_port.py`
- Create: `src/domain/schemas/market_schema.py`
- Test: `tests/domain/test_market_schema.py`

**Interfaces:**
- Produces: `MarketDataPort.get_snapshot() -> MarketSnapshot` (ABC),
  `MarketDataError(Exception)`, `MarketQuote{value: float, change_pct: float}`,
  `MarketSnapshot{bist100, usd_try, eur_try, gold_gram_try: MarketQuote,
  as_of: datetime, stale: bool = False}`.

- [ ] **Step 1: Write the failing test**

`tests/domain/test_market_schema.py`:
```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `venv\Scripts\python.exe -m pytest tests/domain/test_market_schema.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'src.domain.schemas.market_schema'`

- [ ] **Step 3: Write the port**

`src/domain/ports/market_data_port.py`:
```python
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
```

- [ ] **Step 4: Write the schema**

`src/domain/schemas/market_schema.py`:
```python
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
```

- [ ] **Step 5: Run test to verify it passes**

Run: `venv\Scripts\python.exe -m pytest tests/domain/test_market_schema.py -v`
Expected: PASS (2 passed)

- [ ] **Step 6: Commit**

```bash
git add src/domain/ports/market_data_port.py src/domain/schemas/market_schema.py tests/domain/test_market_schema.py
git commit -m "feat: MarketDataPort + MarketSnapshot şeması (piyasa ticker'ı, 1/3)"
```

---

### Task 2: YahooFinanceMarketAdapter

**Files:**
- Create: `src/adapters/market/__init__.py` (boş)
- Create: `src/adapters/market/yahoo_finance_adapter.py`
- Test: `tests/adapters/test_market_adapter.py`

**Interfaces:**
- Consumes: `MarketDataPort`, `MarketDataError` (Task 1), `MarketSnapshot`,
  `MarketQuote` (Task 1).
- Produces: `YahooFinanceMarketAdapter` (implements `MarketDataPort`).

- [ ] **Step 1: Write the failing tests**

`tests/adapters/test_market_adapter.py`:
```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `venv\Scripts\python.exe -m pytest tests/adapters/test_market_adapter.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'src.adapters.market'`

- [ ] **Step 3: Write the adapter**

`src/adapters/market/__init__.py`: (boş dosya)

`src/adapters/market/yahoo_finance_adapter.py`:
```python
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
_SYMBOL_GOLD_OZ = "GC=F"  # COMEX altın vadeli işlemi (USD/oz) — "XAUUSD=X" geçersiz sembol
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `venv\Scripts\python.exe -m pytest tests/adapters/test_market_adapter.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add src/adapters/market/ tests/adapters/test_market_adapter.py
git commit -m "feat: YahooFinanceMarketAdapter (piyasa ticker'ı, 2/3)"
```

---

### Task 3: `GET /market/ticker` — cache orkestrasyonu + wiring

**Files:**
- Create: `src/adapters/api/routers/market_router.py`
- Modify: `src/dependencies.py` (yeni `get_market_data_adapter()`)
- Modify: `src/infrastructure/config/settings.py` (yeni `market_cache_ttl_seconds`)
- Modify: `src/main.py` (import + `include_router`)
- Test: `tests/adapters/test_market_router.py`

**Interfaces:**
- Consumes: `MarketDataPort`/`MarketDataError` (Task 1), `YahooFinanceMarketAdapter`
  (Task 2), mevcut `CachePort`/`get_cache()` (`src/dependencies.py`, değişmedi).
- Produces: `get_market_data_adapter() -> MarketDataPort` (`src/dependencies.py`),
  `GET /market/ticker` endpoint'i (200 `MarketSnapshot`, ya da veri hiç yoksa 204).

- [ ] **Step 1: Write the failing tests**

`tests/adapters/test_market_router.py`:
```python
"""GET /market/ticker testleri — cache hit/miss/stale/204 yolları.
CachePort ve MarketDataPort mock'lanır, gerçek Yahoo çağrısı YOK."""

from datetime import datetime, timezone
from unittest.mock import MagicMock

from src.domain.ports.market_data_port import MarketDataError
from src.domain.schemas.market_schema import MarketQuote, MarketSnapshot


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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `venv\Scripts\python.exe -m pytest tests/adapters/test_market_router.py -v`
Expected: FAIL — `ImportError: cannot import name 'get_market_data_adapter'`

- [ ] **Step 3: Add the settings field**

Modify `src/infrastructure/config/settings.py` — right after the `redis_url`
line (in the `# ── Redis (cache) ──` section, around line 128), add:
```python
    # ── Piyasa ticker'ı (BİST/USD/EUR/gram altın, v2.3) ─────────────────────
    # Yahoo Finance'e her istekte gidilmesin diye CachePort üzerinden TTL'li
    # tutulur (bkz. market_router.py). Redis yoksa (NullCache) fiilen devre dışı.
    market_cache_ttl_seconds: int = 300
```

- [ ] **Step 4: Add the dependency getter**

Modify `src/dependencies.py` — add the import near the other adapter imports
(after `from src.adapters.cache.factory import build_cache`):
```python
from src.adapters.market.yahoo_finance_adapter import YahooFinanceMarketAdapter
from src.domain.ports.market_data_port import MarketDataPort
```
Add the singleton next to `_cache: CachePort = None`:
```python
_market_data_adapter: MarketDataPort = None
```
Add the getter next to `get_cache()`:
```python
def get_market_data_adapter() -> MarketDataPort:
    # Tek implementasyon var (Yahoo Finance) — build_cache()/build_analyzer()
    # gibi bir factory'ye gerek yok, get_search_repository() ile aynı
    # doğrudan-singleton deseni (YAGNI).
    global _market_data_adapter
    if _market_data_adapter is None:
        _market_data_adapter = YahooFinanceMarketAdapter()
    return _market_data_adapter
```

- [ ] **Step 5: Write the router**

`src/adapters/api/routers/market_router.py`:
```python
"""Piyasa verisi — GET /market/ticker (BİST100/USD/EUR/gram altın).

Public, auth gerektirmez (haber okuma gibi şeffaf) — kendi cache'i olduğu
için ayrı bir rate limit de yok. CachePort ile iki katmanlı tutulur:
- "market:snapshot" — TTL'li (settings.market_cache_ttl_seconds), taze veri.
- "market:snapshot:last_good" — 24 saat TTL'li, Yahoo uzun süre kesilse bile
  gösterilecek bir son iyi değer kalsın diye ("ölü besleme çökertmez"
  deseninin piyasa verisi karşılığı, bkz. RSS scraper'lar).
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
        return MarketSnapshot.model_validate({**last_good, "stale": True})
```

- [ ] **Step 6: Wire the router into the app**

Modify `src/main.py` — add the import next to the other router imports
(after `from src.adapters.api.routers.billing_router import router as billing_router`):
```python
from src.adapters.api.routers.market_router import router as market_router
```
Add the include next to `app.include_router(billing_router)`:
```python
app.include_router(market_router)
```

- [ ] **Step 7: Run tests to verify they pass**

Run: `venv\Scripts\python.exe -m pytest tests/adapters/test_market_router.py -v`
Expected: PASS (4 passed)

- [ ] **Step 8: Run the full backend suite (regression check)**

Run: `venv\Scripts\python.exe -m pytest tests/ -v`
Expected: all tests pass (previous count + 6 new: 2 schema + 3 adapter + 4 router... — see Task 9 for the exact final count via `pytest --collect-only`).

- [ ] **Step 9: Commit**

```bash
git add src/adapters/api/routers/market_router.py src/dependencies.py src/infrastructure/config/settings.py src/main.py tests/adapters/test_market_router.py
git commit -m "feat: GET /market/ticker — cache orkestrasyonu + wiring (piyasa ticker'ı, 3/3)"
```

---

### Task 4: Frontend — tipler + API istemcisi

**Files:**
- Modify: `frontend/lib/types.ts` (yeni `MarketQuote`/`MarketSnapshot`)
- Modify: `frontend/lib/api.ts` (yeni `fetchMarketSnapshot()`)

**Interfaces:**
- Consumes: backend `GET /market/ticker` yanıt şekli (Task 3).
- Produces: `MarketQuote`, `MarketSnapshot` (types.ts), `fetchMarketSnapshot():
  Promise<MarketSnapshot | null>` (api.ts) — Task 5/6'nın kullanacağı imza.

- [ ] **Step 1: Add the types**

Modify `frontend/lib/types.ts` — add near `TrendingResponse` (after its
closing brace):
```ts
export interface MarketQuote {
  value: number;
  change_pct: number;
}

export interface MarketSnapshot {
  bist100: MarketQuote;
  usd_try: MarketQuote;
  eur_try: MarketQuote;
  gold_gram_try: MarketQuote;
  as_of: string;
  stale: boolean;
}
```

- [ ] **Step 2: Add the API client function**

Modify `frontend/lib/api.ts`:
1. Add `MarketSnapshot` to the type import at the top of the file (the
   `import type { ... } from "./types";` block) — insert it alphabetically
   next to `Article`.
2. Add a new section at the end of the file (after the "Billing" section):
```ts
// ── Piyasa ticker'ı (v2.3) ───────────────────────────────────────────────────
// Best-effort widget — asla ApiError fırlatmaz, başarısızlıkta null döner ki
// component sessizce render'dan çekilsin (sayfanın geri kalanını etkilemesin).

export async function fetchMarketSnapshot(): Promise<MarketSnapshot | null> {
  try {
    const res = await fetch(`${BASE}/market/ticker`, { credentials: "include" });
    if (res.status === 204 || !res.ok) return null;
    return await res.json();
  } catch {
    return null;
  }
}
```

- [ ] **Step 3: Verify it type-checks**

Run: `cd frontend && npm run build`
Expected: `✓ Compiled successfully` — no unused-export or type errors (the
function isn't called anywhere yet, that's fine, TypeScript doesn't flag
unused exports).

- [ ] **Step 4: Commit**

```bash
git add frontend/lib/types.ts frontend/lib/api.ts
git commit -m "feat: piyasa ticker'ı tipleri + fetchMarketSnapshot (frontend, 1/2)"
```

---

### Task 5: Frontend — `MarketTicker` component + i18n

**Files:**
- Create: `frontend/components/MarketTicker.tsx`
- Modify: `frontend/lib/i18n.ts` (TR/EN anahtarları)

**Interfaces:**
- Consumes: `fetchMarketSnapshot()`, `MarketSnapshot` (Task 4), `useSettings()`
  (`lib/settings-context.tsx`, mevcut), `UI[lang]` (`lib/i18n.ts`, mevcut).
- Produces: `MarketTicker` component (props yok) — Task 6'nın
  `DashboardShell.tsx`'e ekleyeceği.

- [ ] **Step 1: Add the i18n keys**

Modify `frontend/lib/i18n.ts` — TR bloğuna (`day: "Aydınlık", dayTag:
"Gündüz Modu",` satırının hemen altına, `night`/`nightTag`'den sonra) ekle:
```ts
    marketBist: "BİST100", marketUsd: "USD/TL", marketEur: "EUR/TL",
    marketGold: "Gram Altın", marketStale: "gecikmeli",
```
EN bloğuna (`day: "Daylight", dayTag: "Day Mode",` / `night`/`nightTag`
satırlarından sonra) ekle:
```ts
    marketBist: "BIST100", marketUsd: "USD/TRY", marketEur: "EUR/TRY",
    marketGold: "Gold (gram)", marketStale: "delayed",
```

- [ ] **Step 2: Write the component**

`frontend/components/MarketTicker.tsx`:
```tsx
"use client";

import { useEffect, useState } from "react";
import { fetchMarketSnapshot } from "@/lib/api";
import { useSettings } from "@/lib/settings-context";
import { UI } from "@/lib/i18n";
import type { MarketQuote, MarketSnapshot } from "@/lib/types";

const POLL_MS = 60_000;

export function MarketTicker() {
  const { lang } = useSettings();
  const t = UI[lang];
  const [snapshot, setSnapshot] = useState<MarketSnapshot | null>(null);

  useEffect(() => {
    let cancelled = false;
    const load = () => {
      fetchMarketSnapshot().then((s) => {
        if (!cancelled) setSnapshot(s);
      });
    };
    load();
    const id = setInterval(load, POLL_MS);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, []);

  if (!snapshot) return null;

  const locale = lang === "TR" ? "tr-TR" : "en-US";
  const fmt = (n: number, digits = 2) =>
    n.toLocaleString(locale, { minimumFractionDigits: digits, maximumFractionDigits: digits });

  const items: Array<{ label: string; quote: MarketQuote; suffix: string }> = [
    { label: t.marketBist, quote: snapshot.bist100, suffix: "" },
    { label: t.marketUsd, quote: snapshot.usd_try, suffix: " ₺" },
    { label: t.marketEur, quote: snapshot.eur_try, suffix: " ₺" },
    { label: t.marketGold, quote: snapshot.gold_gram_try, suffix: " ₺" },
  ];

  return (
    <div
      style={{
        display: "flex", alignItems: "center", gap: 18,
        padding: "6px 20px", borderBottom: "1px solid var(--border)",
        background: "var(--surface)", overflowX: "auto",
      }}
    >
      {items.map((item) => {
        const up = item.quote.change_pct >= 0;
        return (
          <div key={item.label} style={{ display: "flex", alignItems: "baseline", gap: 6, flexShrink: 0 }}>
            <span style={{
              fontSize: "0.68rem", fontWeight: 800, letterSpacing: "0.04em",
              color: "var(--text3)", textTransform: "uppercase",
            }}>
              {item.label}
            </span>
            <span style={{ fontSize: "0.82rem", fontWeight: 700, color: "var(--text)" }}>
              {fmt(item.quote.value)}{item.suffix}
            </span>
            <span style={{ fontSize: "0.72rem", fontWeight: 700, color: up ? "var(--pos)" : "var(--neg)" }}>
              {up ? "▲" : "▼"} {fmt(Math.abs(item.quote.change_pct))}%
            </span>
          </div>
        );
      })}
      {snapshot.stale && (
        <span style={{ fontSize: "0.68rem", color: "var(--text3)", fontStyle: "italic", flexShrink: 0 }}>
          ({t.marketStale})
        </span>
      )}
    </div>
  );
}
```

- [ ] **Step 3: Verify it type-checks**

Run: `cd frontend && npm run build`
Expected: `✓ Compiled successfully` (component isn't rendered anywhere yet —
Task 6 wires it in; an unrendered-but-exported component is not a build error).

- [ ] **Step 4: Commit**

```bash
git add frontend/components/MarketTicker.tsx frontend/lib/i18n.ts
git commit -m "feat: MarketTicker component'i (frontend, 2/2)"
```

---

### Task 6: Dashboard'a bağla + uçtan uca doğrulama

**Files:**
- Modify: `frontend/app/dashboard/DashboardShell.tsx`

**Interfaces:**
- Consumes: `MarketTicker` (Task 5).

- [ ] **Step 1: Wire the component in**

Modify `frontend/app/dashboard/DashboardShell.tsx` — add the import next to
the `LiveTicker` import:
```tsx
import { MarketTicker } from "@/components/MarketTicker";
```
Add `<MarketTicker />` between `<Navbar />` and `<LiveTicker />`:
```tsx
      <div style={{ minHeight: "100vh" }}>
        <Navbar />
        <MarketTicker />
        <LiveTicker />
        <main style={{ maxWidth: 1280, margin: "0 auto", padding: "28px 20px" }}>
```

- [ ] **Step 2: Verify it type-checks and builds**

Run: `cd frontend && npm run build`
Expected: `✓ Compiled successfully`, `/dashboard` route listed in the output
table (route sizes may shift slightly — that's expected, not a failure).

- [ ] **Step 3: Manual smoke test (dev server)**

Bu adım container gerektirir — Docker Desktop kapalıysa atla ve kullanıcıya
"Docker açıkken `docker compose up -d` sonrası `/dashboard`'ı kontrol et"
diye bildir.

Run: `docker compose up -d app frontend db redis` (redis dahil — cache'siz
NullCache modunda her poll canlı Yahoo çağrısı yapar, davranış yine doğru
ama gereksiz yere yavaş görünebilir).
Tarayıcıda `http://localhost:3000/dashboard` aç, Navbar altında piyasa
şeridinin göründüğünü doğrula. `docker logs nexstream_engine --tail 30` ile
`/market/ticker` isteğinin 200 döndüğünü kontrol et.

- [ ] **Step 4: Commit**

```bash
git add frontend/app/dashboard/DashboardShell.tsx
git commit -m "feat: piyasa ticker'ını dashboard'a bağla"
```

## Self-Review Notu (plan yazarı için, uygulama öncesi referans)

- **Spec kapsamı:** Tüm spec bölümleri (port/adapter, cache, endpoint,
  frontend, hata toleransı, test) Task 1-6'da karşılanıyor. Tek kasıtlı
  sapma: factory dosyası yok (Global Constraints'te gerekçelendirildi,
  spec'in "kompozisyon noktası" diline aykırı değil — `get_market_data_
  adapter()` zaten o rolü görüyor).
- **Tip tutarlılığı:** `MarketQuote`/`MarketSnapshot` alan adları (Python
  Task 1 ↔ TypeScript Task 4) birebir aynı (`bist100`, `usd_try`, `eur_try`,
  `gold_gram_try`, `as_of`, `stale`, `value`, `change_pct`) — FastAPI/Pydantic
  otomatik `snake_case` JSON üretir, frontend tipleri kasıtlı olarak aynı
  adları kullanıyor (dönüştürme katmanı yok, YAGNI).
- **Placeholder taraması:** Yok — her adımda çalıştırılabilir kod var.
