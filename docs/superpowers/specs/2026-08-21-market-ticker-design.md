# Piyasa Ticker'ı (BİST100 / USD / EUR / Gram Altın) — Tasarım

**Tarih:** 21 Ağustos 2026
**Durum:** Onay bekliyor (brainstorming → writing-plans geçişi öncesi)
**Kaynak:** Canlı kullanıcı testi geri bildirimi (20-21 Ağu 2026, telefon
kullanıcıları) — "haberler sekmesine anlık BİST/döviz/altın değerleri
ekleyebiliriz."

## Amaç

Dashboard'da (haber akışının üstünde) sürekli görünen, ~5 dakikada bir
tazelenen küçük bir piyasa şeridi: BİST100 endeksi, USD/TRY, EUR/TRY,
gram altın (TRY). Herkese açık — tier-gating yok, corroboration rozeti
gibi bir şeffaflık/bilgi özelliği muamelesi görür.

## Mimari

Hexagonal desene uyumlu — yeni bir port + adapter, mevcut composition
pattern'i (`factory.py` dosyaları) tekrarlar.

```
domain/ports/market_data_port.py     # MarketDataPort (ABC)
domain/schemas/market_schema.py      # MarketSnapshot (Pydantic response)
adapters/market/
  ├── yahoo_finance_adapter.py       # YahooFinanceMarketAdapter — somut implementasyon
  └── factory.py                     # build_market_data_adapter() — kompozisyon noktası
adapters/api/routers/market_router.py # GET /market/ticker
```

`NewsService`'e dokunulmaz — piyasa verisi haber domain'inden tamamen
bağımsız bir kaygı, kendi ince orkestrasyonunu (adapter + cache) router
seviyesinde yapar; ayrı bir `MarketService` gerekmeyecek kadar ince
(tek metot, tek adapter çağrısı + cache lookup).

### `MarketDataPort`

```python
class MarketDataPort(ABC):
    @abstractmethod
    def get_snapshot(self) -> MarketSnapshot: ...
```

Tek metot — `analyze_or_raise` deseniyle aynı: hata varsa
`MarketDataError` fırlatır, nötr/boş fallback'i ÇAĞIRAN taraf (router)
karar verir (cache'teki son değeri kullan ya da boş dön).

### `MarketSnapshot` şeması

```python
class MarketQuote(BaseModel):
    value: float
    change_pct: float

class MarketSnapshot(BaseModel):
    bist100: MarketQuote
    usd_try: MarketQuote
    eur_try: MarketQuote
    gold_gram_try: MarketQuote
    as_of: datetime           # UTC, veri Yahoo'dan ne zaman çekildi
    stale: bool = False       # cache'teki son BAŞARILI değer mi (canlı değil)
```

### Veri kaynağı — Yahoo Finance (resmi olmayan, key gerektirmez)

`https://query1.finance.yahoo.com/v8/finance/chart/{symbol}` — `/v7/finance/quote`
DEĞİL: quote endpoint'i 2023'ten beri bir "crumb" cookie-exchange dansı
gerektiriyor (kırılgan), chart endpoint'i gerektirmiyor. Bedeli: batch
sorgu yok, 4 sembol için 4 ayrı GET (`asyncio.gather` ile paralel).
Semboller: `XU100.IS` (BİST100), `USDTRY=X`, `EURTRY=X`, `XAUUSD=X`
(altın spot, USD/ons).

Her yanıttan `chart.result[0].meta.regularMarketPrice` ve
`.previousClose` (yoksa `.chartPreviousClose`) okunur, `change_pct =
(price - previousClose) / previousClose * 100` hesaplanır.

**Gram altın TL:** ayrı bir sembol yok, iki değerden türetilir:
```
gram_try         = (xau_usd_price      / 31.1034768) * usdtry_price
gram_try_prev    = (xau_usd_previous   / 31.1034768) * usdtry_previous
change_pct       = (gram_try - gram_try_prev) / gram_try_prev * 100
```

**Bilinen risk (RSS scraper'larla aynı kategori):** Yahoo resmi bir API
değil, User-Agent spoofing gerektirir (`requests` varsayılan UA'sı
403 alabilir — tarayıcı benzeri bir `User-Agent` header'ı zorunlu),
format/erişim habersiz değişebilir. Fail-open ele alınır (aşağıya
bak) — worker/app hiçbir zaman bu yüzden çökmez.

## Cache

Mevcut `CachePort` (Redis varsa `RedisCacheAdapter`, yoksa
`NullCacheAdapter` — zaten `get_cache()` ile `dependencies.py`'de
singleton) TTL ~300sn (`MARKET_CACHE_TTL_SECONDS`, yeni env var,
varsayılan 300) ile kullanılır. Anahtar: `"market:snapshot"`.

Akış (router handler'ı):
1. `cache.get("market:snapshot")` → varsa ve `age < TTL` ise direkt dön.
2. Yoksa/eskiyse `market_adapter.get_snapshot()` çağır.
   - Başarılı → cache'e yaz (TTL + ayrıca `"market:snapshot:last_good"`
     anahtarına TTL'siz/uzun-TTL'li olarak da yaz — Yahoo uzun süre
     kesilirse bile son bilinen değer elde kalsın), `stale=False` dön.
   - Başarısız (`MarketDataError`) → `"market:snapshot:last_good"`'u
     dene; varsa `stale=True` işaretleyip onu dön; hiç yoksa (ilk
     çalıştırmadan beri hiç başarı yoksa) `204 No Content` dön —
     frontend ticker'ı hiç göstermez.

Bu, Redis yoksa (dev/NullCache) her istek Yahoo'ya gider demek — düşük
trafikte sorun değil, mevcut projenin "cache'siz çalışmak bir hata
değil bir moddur" felsefesiyle tutarlı.

## Endpoint

`GET /market/ticker` — yeni `market_router.py`, `main.py`'de
`app.include_router(market_router.router)`. Auth YOK (haber okuma gibi
public), rate limit YOK (zaten kendi cache'i var, ucuz bir endpoint).
Yanıt: `MarketSnapshot` ya da veri hiç yoksa `204`.

## Frontend

`frontend/components/MarketTicker.tsx` — Navbar'ın hemen altında,
sadece `/dashboard` ve `/dashboard/search` sayfalarında (landing'de
yok — kayıtsız ziyaretçiye "canlı ürün" hissi vermek dashboard'a özel
kalsın, landing zaten kendi hero'sunu koruyor). `useEffect` ile mount'ta
+ her 60 saniyede bir `fetch('/api/market/ticker')` (nginx `/api/`
prefix'i mevcut routing şemasıyla `/market/ticker`'a düşer — CLAUDE.md
"nginx routing" notuna bak). 204 ya da hata durumunda component hiç
render olmaz (`return null`), sayfanın geri kalanını etkilemez.

4 kalem yan yana (mobilde yatay scroll, `overflow-x: auto` — CLAUDE.md
responsive kuralına uy): BİST100, USD, EUR, Gram Altın. Her biri:
etiket + değer + değişim% (`pos`/`neg` token renkleriyle ok işareti,
tema bağımsız — sabit renk YOK, `var(--pos)`/`var(--neg)`). `stale:
true` ise değerlerin yanında küçük bir "gecikmeli" ibaresi (i18n'li,
`lib/i18n.ts`'e yeni anahtarlar).

i18n: `UI[lang]` içine `marketBist`, `marketUsd`, `marketEur`,
`marketGold`, `marketStale` gibi anahtarlar (TR/EN) — CLAUDE.md
"i18n/dil dallanması" kuralına uy, hardcoded metin yazma.

## Hata Toleransı Özeti

| Senaryo | Davranış |
|---|---|
| Yahoo 403/timeout/format değişti | `MarketDataError` fırlar, loglanır, cache'teki son iyi değer + `stale:true` döner |
| Hiç cache yok + Yahoo başarısız (ilk çalıştırma) | `204`, ticker hiç görünmez |
| Redis yok (NullCache) | Her istek canlı çeker — düşük trafikte kabul edilebilir |
| Frontend fetch başarısız | Component `null` render eder, sayfa etkilenmez |

## Test

- `tests/adapters/test_market_adapter.py` — `YahooFinanceMarketAdapter`,
  HTTP mock'lanır (gerçek çağrı YOK, proje kuralı), gram altın
  hesaplama formülü ayrı test edilir (bilinen girdi → beklenen çıktı).
- `tests/adapters/test_market_router.py` — cache hit/miss/stale/204
  yollarının hepsi, `CachePort` mock'lanır.
- Frontend: `npm run build` (tip kontrolü + prod build) — component
  çalışırken container ile ilgili gotcha'ya dikkat (host'ta build
  container ayaktayken çalıştırılmaz).

## Kapsam Dışı (bilinçli)

- Geçmiş grafik/sparkline — sadece anlık değer + günlük değişim%.
- WebSocket canlı akışı (`/ws/feed`) ile entegrasyon — ayrı bir kaygı,
  ticker kendi düşük frekanslı polling'ini kullanır, mevcut WS akışına
  yeni bir mesaj tipi eklemek gereksiz karmaşıklık (YAGNI).
- Diğer döviz/emtia kalemleri (gümüş, Euro-Dolar paritesi, çeyrek
  altın vb.) — talep gelirse ayrı bir roadmap maddesi.
