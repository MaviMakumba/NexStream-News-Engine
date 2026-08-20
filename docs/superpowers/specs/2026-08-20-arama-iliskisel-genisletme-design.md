# Arama — ilişkisel sorgu genişletme (query expansion) — Tasarım

**Tarih:** 20 Ağustos 2026
**Dal:** `main`'den yeni bir kısa ömürlü feature branch açılacak
**Durum:** Tasarım onaylandı, uygulama bekliyor

---

## Problem

Mevcut `hybrid_search` (semantik ChromaDB + anahtar kelime Postgres) sadece
sorgudaki kelimelerin kendisini (ve TR ek-kırpılmış köklerini) arıyor.
Kullanıcı bugün iki somut örnek verdi:

- **"İstanbul" arattığında Beykoz ilçesindeki bir haber çıkmıyor** — "Beykoz"
  kelimesi haberde geçse bile "İstanbul" kelimesi geçmiyorsa hiç eşleşmiyor.
- **"futbol" arattığında içinde "futbol" kelimesi geçmeyen ama konu olarak
  futbol olan (Beşiktaş/Fenerbahçe/Galatasaray transfer haberi gibi) sonuçlar
  çıkmıyor.**

Bu, saf kelime eşleşmesinin doğal bir sınırı — embedding tabanlı semantik arama
da bu tür taksonomik/hiyerarşik ilişkileri (şehir→ilçe, spor dalı→takım)
güvenilir şekilde yakalamıyor (genel amaçlı çok dilli bir embedding modeli,
"anlam benzerliği" ölçer, "parça-bütün" ilişkisini değil).

Aynı oturumda ayrı bir bug olarak `_keyword_relevance`'ın ham substring
eşleşmesi ("Adana" → kök "ada" → "havadan" kelimesinin ORTASINDA yanlış
eşleşme) zaten düzeltildi (bkz. CLAUDE.md, 20 Ağu 2026 notu) — bu spec o
düzeltmenin ÜZERİNE, ayrı bir iyileştirmedir.

---

## Çözüm Özeti

LLM tabanlı (Groq, zaten kullanılan altyapı) sorgu genişletme: arama sorgusu
geldiğinde Groq'a "bu sorguyla ilişkili 3-6 ek terim üret" diye sorulur,
sonuç Redis'te (varsa) 30 gün cache'lenir, genişletilmiş terimler **sadece
keyword tarafına** düşük ağırlıkla eklenir. Semantik taraf hiç değişmez.

**Spike ile doğrulandı (20 Ağu 2026):** Gerçek Groq çağrısı "istanbul" için
`Fatih, Beyoğlu, Kadıköy, Şişli, Üsküdar, Bakırköy, Ümraniye, Maltepe,
Sarıyer, Çekmeköy` üretti — doğru ilçe isimleri, doğru JSON formatı, 0.8sn.
Aynı spike'ta Groq günlük token kotasının (%99.9 dolu) BUGÜNE özel bir
çakışmadan (local + prod aynı `GROQ_API_KEY`'i aynı anda kullandı) kaynaklandığı
da netleşti — normal prod trafiği tek başına çok düşük (48 saatte tek "yeni
haber" partisi). Detay: CLAUDE.md "Local ve prod AYNI paylaşılan
`GROQ_API_KEY`'i kullanıyor" notu.

---

## 1. Yeni port + adapter

### `src/domain/ports/query_expansion_port.py` (yeni)

```python
class QueryExpansionPort(ABC):
    @abstractmethod
    def expand(self, query: str) -> list[str]: ...
```

`AnalysisPort`/`EmbeddingPort` ile aynı desen — tek sorumluluk, domain hiçbir
somut implementasyonu bilmez.

### `src/adapters/analysis/groq_query_expander.py` (yeni)

Groq'a küçük bir prompt gönderir (spike'ta doğrulanan prompt şablonu
kullanılır — kurallar: şehir/il ise ilçe, spor dalıysa takım, ekonomik/siyasi
kavramsa kurum/kişi/parti; sorgunun kendisini tekrar ETME; emin değilse az
terim üret). `reasoning_effort="low"`, `max_tokens` düşük tutulur (spike'ta
~300 yeterliydi). **Her hata yolu** (429, timeout, 404 model_not_found, JSON
parse hatası) yakalanır, loglanır, **boş liste** döner — hiçbir exception
çağırana sızmaz (projenin "Exception'ları yut, logla, fallback dön" kuralı).

### `src/adapters/analysis/caching_query_expander.py` (yeni)

`QueryExpansionPort`'u sarmalayan bir decorator: `CachePort` (mevcut,
`dependencies.py::get_cache()`) üzerinden önce cache'e bakar, miss'te alttaki
`GroqQueryExpander`'ı çağırıp sonucu cache'ler.

- **Cache key:** `f"qexp:{query.strip().lower()}"`
- **TTL (dolu sonuç):** 30 gün — coğrafi/taksonomik ilişkiler zamanla değişmez.
- **TTL (boş sonuç):** 1 saat — geçici bir Groq arızasını kalıcı "hiç
  genişletme yok" damgası yapmamak için.
- Cache okuma/yazma hatası genişletmeyi engellemez, sessizce cache'siz devam
  eder (aynı fail-open felsefesi).

### `src/adapters/analysis/factory.py` (genişler)

`build_query_expander() -> Optional[QueryExpansionPort]` — `settings.
search_query_expansion_enabled` false ise `None` döner (özellik komple kapalı).
True ise `CachingQueryExpander(GroqQueryExpander(), get_cache())`.

**Neden ayrı bir yedek LLM (HF vb.) YOK:** `FallbackAnalyzer` (Groq→HF→nötr)
haber analizinde var çünkü sonuç DB'ye kalıcı yazılıyor — boş kalırsa veri
kalitesi kalıcı düşer. Query expansion her aramada yeniden hesaplanan, hiçbir
şeyi kalıcı bozmayan bir zenginleştirme; Groq başarısız olursa arama sadece
eski (genişletmesiz) haline döner. Ayrı bir yedek LLM eklemek burada YAGNI'ya
aykırı olur.

---

## 2. `NewsService` entegrasyonu

`__init__`'e opsiyonel bağımlılık: `query_expander: Optional[QueryExpansionPort]
= None` (search_repository gibi — verilmezse özellik sessizce devre dışı,
mevcut testler ve davranış DEĞİŞMEDEN kalır).

### `hybrid_search` içinde

```python
expanded_terms: List[str] = []
if self.query_expander:
    try:
        expanded_terms = self.query_expander.expand(query)
    except Exception as e:
        logger.warning("Sorgu genişletme başarısız, orijinal sorguyla devam: %s", e)
```

- **Semantik taraf DOKUNULMAZ** — genişletilmiş terimler embedding sorgusuna
  karışmaz (orijinal sorgunun anlamını sulandırma riski).
- **SQL aday havuzu:** `query_terms` listesine (mevcut `_tokenize` çıktısı)
  `expanded_terms`'ten türetilen terimler de eklenir — yoksa o makale DB'den
  hiç çekilmez, `_keyword_relevance` onu hiç göremez.
- **Skorlama:** `_keyword_relevance` yeni bir opsiyonel `secondary_terms`
  parametresi alır (varsayılan `None`, eski çağrılar/testler kırılmaz):

  ```
  final_relevance = primary_relevance + secondary_relevance * _EXPANSION_WEIGHT
  ```

  `_EXPANSION_WEIGHT = 0.4` (modül sabiti, `_DOUBLE_HIT_BONUS` gibi). Coverage
  hesabı primary ve secondary için AYRI yapılır (n farklı) — secondary'nin
  kelime-başı eşleşme kuralı (mevcut `\b` regex düzeltmesi) aynen uygulanır,
  yeni bir substring-bug riski yaratılmaz. Secondary skor asla primary'yi
  domine edemez (0.4 çarpanı + `min(total, 1.0)` tavanı zaten var).

---

## 3. Config + Dependency Injection

`src/infrastructure/config/settings.py`'ye yeni env var:

- `search_query_expansion_enabled: bool = True` — tek satırla özelliği
  komple kapatabilmek için (worker/analiz etkilenmez).

`src/dependencies.py::get_news_service()`'e `query_expander=build_query_expander()`
eklenir (mevcut `search_repository` DI noktasıyla aynı yerde). **DB migration
gerekmiyor** — yeni bir tablo/kolon yok, tamamen stateless bir zenginleştirme
katmanı (cache Redis'te, kalıcı veri Postgres'e hiç yazılmıyor).

---

## 4. Test stratejisi

- `GroqQueryExpander`: mock HTTP — başarı, 429, timeout, bozuk-JSON
  senaryolarının HEPSİNDE boş liste dönmeli, exception fırlamamalı.
- `CachingQueryExpander`: sahte `CachePort` + sahte alt-expander — cache
  hit'te alt-expander'a hiç gidilmediğini, miss'te gidilip sonucun
  cache'lendiğini, boş sonucun kısa TTL'le cache'lendiğini doğrula.
- `NewsService.hybrid_search`: `query_expander=None` iken **mevcut TÜM
  testler değişmeden geçmeli**. Yeni testler: mock expander ile secondary
  terim skorunun primary'yi domine etmediğini, SQL aday havuzuna secondary
  terimlerin eklendiğini doğrula.
- `_keyword_relevance`: eski çağrılar (tek parametre) davranış değiştirmeden
  geçmeli; yeni `secondary_terms` parametresiyle coverage hesabının doğru
  ayrıştığını doğrula.

---

## Kapsam Dışı (bu turda YAPILMAYACAK)

- Semantik embedding sorgusuna genişletme eklemek (dilution riski, ayrı bir
  değerlendirme ister).
- Ayrı bir yedek LLM (HuggingFace) — yukarıda gerekçelendirildi.
- Statik TR il-ilçe / konu-varlık sözlüğü (LLM yaklaşımı onaylandığı için
  şimdilik gerekmiyor — ileride Groq güvenilirliği sorun çıkarırsa bir
  alternatif olarak değerlendirilebilir).
