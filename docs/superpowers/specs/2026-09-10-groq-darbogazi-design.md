# Groq rate-limit darboğazı — havuz bölme + adil kuyruklama + near-dup önceliği — Tasarım

**Tarih:** 10 Eylül 2026
**Dal:** `main`'den yeni bir kısa ömürlü feature branch açılacak
**Durum:** Tasarım onaylandı, uygulama bekliyor
**İlgili:** CLAUDE.md roadmap madde 25 + 27 (kaynak sağlığı taraması)

---

## Problem

10 Eylül'deki kaynak sağlığı taramasında (roadmap #27) canlı worker log'u
izlenirken yakalandı: startup-scrape SADECE registry'nin 1. kaynağını (TRT
Haber, 3 yeni haber) bitirmek için **7.5 dakika** sürdü — tek bir Groq
rate-limit beklemesi 184 saniyeydi. Gerçek `x-ratelimit-*` header'ları canlı
ölçüldü: `openai/gpt-oss-20b`'nin TPM tavanı **8000 token/dakika** — mevcut
proaktif throttle (31 Ağu, `_throttle_for_remaining_budget`) bunu doğru
yönetiyor ama TEK modelin kovası, 17 kaynağın TÜM trafiğini karşılamaya
yetmiyor.

Kök neden zincirleme: `scheduler_service.py` her 10dk'da 17 kaynağı **hep aynı
sabit sırayla** (`settings.scrape_sources`) Kafka'ya kuyruklar; worker FIFO
tüketir, her mesaj kendi kaynağını tam bitirene kadar sıradakine geçmez.
Worker throttle'a takılıp geride kalınca, her yeni tick kuyruğun SONUNA 17
mesaj daha ekler — sondaki kaynaklar (Guardian Tech, TechCrunch, Hacker News,
The Verge) hiçbir zaman öne geçemez. Prod DB'den çekilen gerçek 3 günlük
trafik bunu doğruluyor: bu 4 kaynağın her biri sadece **5 haber/3gün**
almış (diğer kaynaklar 35-240 arası) — tamamen kesilmemiş ama ciddi şekilde
aç bırakılmış.

Ayrıca: `is_near_duplicate` kontrolü bugün Groq analizinden SONRA çalışıyor —
near-duplicate haberler bile tam (pahalı) analiz alıyor, boşa Groq bütçesi
harcanıyor.

---

## Çözüm Özeti

Üç bağımsız ama birlikte çalışan değişiklik:

1. **Havuz bölme:** Ana pipeline artık TEK modele (`gpt-oss-20b`) değil, iki
   modele (`gpt-oss-20b` + `qwen/qwen3.8-27b`) dinamik olarak dağıtılıyor —
   her Groq çağrısında hangi modelin bütçesi daha rahatsa oraya gidiliyor.
   Statik kaynak→model ataması YOK, yeni bir kaynak eklendiğinde otomatik
   dengeleniyor.
2. **Scheduler rotasyonu:** `send_scrape_command` artık kaynakları hep aynı
   sırayla değil, her tick'te farklı bir başlangıç noktasından yayınlıyor —
   worker geride kalsa bile hiçbir kaynak sürekli son sırada kalamaz.
3. **Near-duplicate önceliği:** Dedup kontrolü Groq analizinden ÖNCEye
   alınıyor; near-duplicate çıkan haberler Groq'a hiç gitmiyor, analiz
   alanları ChromaDB'nin zaten bulduğu en yakın komşudan kopyalanıyor (nötr
   fallback değil — gerçek, isabetli bir analiz, üstelik ücretsiz).

**Spike ile doğrulandı (10 Eylül 2026):** `gpt-oss-20b`, `gpt-oss-120b`,
`qwen/qwen3.8-27b`, `qwen/qwen3.6-27b` için gerçek Groq çağrılarıyla
`x-ratelimit-limit-tokens` ölçüldü — hepsi 8000 TPM, **bağımsız kovalar**
(aynı anda farklı `remaining` değerleri gözlendi). `qwen/qwen3.6-27b`
`<think>` etiketini content içine gömüyor (mevcut JSON parser'ı kırar,
eski `llama-3.1-8b-instant` felaketiyle aynı sınıf hata) — **kullanılmayacak**.
`qwen/qwen3.8-27b` temiz JSON döndü, `gpt-oss-120b` gibi reasoning/content
ayrımı sorunsuz. Prod DB'den 3 günlük gerçek trafik (Sözcü 240 ... Hacker
News 5) greedy bin-packing ile hesaplandı — iki havuz ~703/702 dengeli
çıkıyor (bu tablo artık statik bir atama değil, sadece canlıda gerçekten
dengeli dağılıp dağılmadığını doğrulamak için bir referans).

---

## 1. Havuz bölme — `PooledGroqAnalyzer`

### `src/adapters/analysis/groq_analyzer.py` (genişler)

`GroqAnalyzer.__init__` zaten `model` parametresi alıyor (şu an hep
`"openai/gpt-oss-20b"` sabit) — bunu gerçek bir parametre haline getir:

```python
def __init__(self, model: str = "openai/gpt-oss-20b"):
    self.model = model
    ...
```

`_throttle_for_remaining_budget` ve `_record_token_usage`, okudukları
`remaining`/`reset` değerlerini artık sadece log'lamıyor, modül seviyesinde
paylaşılan bir duruma da yazıyor (aşağıya bkz).

### `src/adapters/analysis/groq_pool.py` (yeni)

```python
import threading

_budget_lock = threading.Lock()
_remaining_tokens: dict[str, int] = {}  # model -> son bilinen kalan TPM

def record_remaining(model: str, remaining: int) -> None:
    with _budget_lock:
        _remaining_tokens[model] = remaining

def pick_least_loaded(models: list[str]) -> str:
    """Hiç çağrılmamış model tam bütçeli sayılır (önce o denenir)."""
    with _budget_lock:
        return max(models, key=lambda m: _remaining_tokens.get(m, float("inf")))


class PooledGroqAnalyzer(AnalysisPort):
    def __init__(self, models: list[str]):
        self._analyzers = {m: GroqAnalyzer(model=m) for m in models}

    def analyze_text(self, text: str) -> dict:
        model = pick_least_loaded(list(self._analyzers))
        return self._analyzers[model].analyze_text(text)
```

`GroqAnalyzer._throttle_for_remaining_budget` içinde `record_remaining
(self.model, remaining)` çağrısı eklenir — mevcut proaktif-bekleme akışına
tek satırlık bir yan etki, davranış değişmez.

**Thread-safety:** worker çağrıları `loop.run_in_executor(None, ...)` ile
thread pool'da çalışıyor — `_budget_lock` bu yüzden gerekli (basit bir
`threading.Lock`, aşırı mühendislik değil, tek bir dict koruyor).

**Neden kaynak→model statik ataması YOK:** kullanıcı sorusu üzerine
netleşti — dinamik seçim yeni kaynak eklerken hiçbir ek karar gerektirmiyor,
mevcut header-okuma mekanizmasının doğal bir uzantısı.

### `src/adapters/analysis/factory.py` (değişir)

`build_analyzer()` artık ana pipeline için `PooledGroqAnalyzer(["openai/
gpt-oss-20b", "qwen/qwen3.8-27b"])` döndürür (Groq yapılandırılıysa; model
listesi `settings.groq_model_pool` — virgülle ayrılmış env var, varsayılan
bu iki model). RAG'ın `GroqQuestionAnswerer`/`GroqQueryExpander`'ı
`gpt-oss-120b`'ye AYRI kalmaya devam eder, bu havuza hiç dahil değil —
mevcut izolasyon bozulmaz.

**Gözlemlenebilirlik:** `groq_tokens_total{model=...}` metriği zaten model
bazlı — yeni bir metrik gerekmiyor, Grafana'da havuzun gerçekten dengeli
dağılıp dağılmadığı doğrudan izlenebilir.

### Config

`src/infrastructure/config/settings.py`'ye yeni env var:

- `groq_model_pool: str = "openai/gpt-oss-20b,qwen/qwen3.8-27b"` — virgülle
  ayrılmış model listesi. Tek bir değer verilirse (veya boşsa) `PooledGroqAnalyzer`
  tek elemanlı listeyle de çalışır (davranış = bugünkü tek-model hali,
  geriye dönük uyumlu). DB migration gerekmiyor.

---

## 2. Scheduler rotasyonu

### `src/adapters/scheduling/scheduler_service.py` (değişir)

```python
_tick_index = 0  # modül seviyesi, process ömrü boyunca kalıcı

async def send_scrape_command():
    global _tick_index
    sources = [s.strip() for s in settings.scrape_sources.split(",") if s.strip()]
    if sources:
        offset = _tick_index % len(sources)
        sources = sources[offset:] + sources[:offset]
        _tick_index += 1
    for source in sources:
        ...  # değişmez
```

Scheduler'ın kendi tasarım ilkesi ("kendisi iş YAPMAZ, sadece üretir")
korunuyor — DB'ye dokunmuyor, sadece process-içi bir sayaç. Restart'ta
`_tick_index` sıfırlanır, bu zararsız (rotasyon zaten olasılıksal bir
adalet sağlıyor, kesin sıra garantisi değil).

**Kapsam dışı (bu turda):** DB'den `MAX(created_at) GROUP BY source` okuyup
"en bayat kaynaktan başla" — daha güçlü ama scheduler'ın DB'ye hiç
dokunmama ilkesini kırıyor, mevcut trafik ölçeğinde (günde ~470 haber)
gereksiz. Rotasyon yetersiz kalırsa ikinci adım olarak değerlendirilir.

---

## 3. Near-duplicate önceliği

### `src/application/services/news_service.py::update_news_from_source` (değişir)

Mevcut sıra: analiz → metadata zenginleştirme → dedup kontrolü → kaydet.
Yeni sıra: dedup kontrolü → (near-dup ise komşudan kopyala, DEĞİLSE analiz
et) → metadata zenginleştirme → kaydet.

```python
for i, article in enumerate(new_articles):
    if i > 0:
        await asyncio.sleep(settings.groq_request_interval_seconds)

    neighbor = None
    if self.search_repository:
        try:
            neighbor = self.search_repository.find_near_duplicate_source(article)
        except Exception as e:
            logger.warning("Dedup kontrolü başarısız, devam ediliyor: %s", e)

    if neighbor is not None:
        article.is_duplicate = True
        self._copy_analysis_from(article, neighbor)
    else:
        result = await loop.run_in_executor(None, self.analyzer.analyze_text, article.content)
        self._apply_analysis(article, result)

    ...  # metadata zenginleştirme + kaydet aynen kalır
```

### `src/adapters/search/chroma_search_repository.py` (değişir)

Yeni bir metod EKLENİR, mevcut `is_near_duplicate(article) -> bool`
DOKUNULMADAN kalır (`test_chroma_search_repository.py` +
`test_semantic_dedup.py` onu doğrudan test ediyor, kırılmamalı):

```python
def find_near_duplicate_source(self, article: Article, threshold: float = 0.92) -> Optional[int]:
    """is_near_duplicate ile AYNI sorgu, ama eşleşirse komşunun id'sini döner
    (None = near-duplicate değil). `is_near_duplicate` bunun üstüne ince bir
    sarmalayıcı olarak yeniden yazılabilir (davranış değişmez, kod tekrarı
    azalır) — ama bu zorunlu değil, iki metod bağımsız da kalabilir."""
```

### `NewsService._copy_analysis_from(article, neighbor_id)` (yeni)

`self.repository`'den `neighbor_id` ile makaleyi çeker, `summary`,
`sentiment_score`, `sentiment_label`, `entities`, `topic` alanlarını
kopyalar. Komşu makale herhangi bir nedenle bulunamazsa (silinmiş, DB
hatası) **sessizce Groq'a düşer** (fail-open — mevcut projenin genel
felsefesiyle tutarlı, `except Exception: pass` + `analyzer.analyze_text`
fallback'i).

**Attribution notu:** kopyalanan özet farklı bir kaynağın metninden
üretilmiş olsa da, near-duplicate eşiği (0.92 benzerlik) zaten neredeyse
birebir aynı metni gerektiriyor — kartın kendi source/title/url alanları
DEĞİŞMİYOR, sadece analiz alanları paylaşılıyor. Telif değerlendirmesi
(CLAUDE.md, 24 Ağu) bunu etkilemiyor (kaynak gösterimi aynen korunuyor).

---

## Uygulama sırası

Üç değişiklik birbirinden BAĞIMSIZ (ayrı dosyalar, ayrı test dosyaları,
biri olmadan diğeri de çalışır) — proje kuralı gereği (kısa ömürlü feature
branch) tek bir dev branch yerine **3 ayrı PR** olarak sırayla uygulanması
önerilir, her biri kendi başına deploy edilip prod'da gözlemlenebilir:

1. Near-duplicate önceliği (madde 3) — en düşük riskli, en hızlı gözlenebilir
   Groq tasarrufu.
2. Havuz bölme (madde 1) — asıl kapasite artışı.
3. Scheduler rotasyonu (madde 2) — en küçük değişiklik, adalet garantisi.

---

## 4. Test stratejisi

- **`PooledGroqAnalyzer`:** iki sahte alt-analyzer, `pick_least_loaded`'ın
  gerçekten daha yüksek `remaining` değerine sahip modeli seçtiğini,
  hiç çağrılmamış modelin öncelikli denendiğini, `record_remaining`'in
  thread-safe çalıştığını (art arda çağrılarda veri yarışı olmadığını)
  doğrula.
- **`GroqAnalyzer(model=...)`:** parametrik model artık testlerde de
  geçirilebiliyor mu, varsayılan `gpt-oss-20b` eski davranışı bozmuyor mu.
- **`scheduler_service.send_scrape_command`:** art arda üç çağrıda farklı
  başlangıç noktalarından yayınlandığını, tüm kaynakların her zaman TAM
  olarak bir kez gönderildiğini (rotasyon sırayı bozuyor, kaynak
  KAYBETMİYOR/YİNELEMİYOR) doğrula.
- **`update_news_from_source`:** near-duplicate çıkan bir makalenin
  `analyzer.analyze_text`'i HİÇ çağırmadığını, komşudan doğru alanları
  kopyaladığını; near-duplicate DEĞİLSE eski akışın (Groq çağrısı) aynen
  çalıştığını; komşu bulunamazsa Groq'a fail-open düştüğünü doğrula.
- **Mevcut testler:** `search_repository=None` / `query_expander=None` gibi
  opsiyonel bağımlılık yokken davranışın DEĞİŞMEDEN geçmesi gerekiyor
  (mevcut proje kuralı).

---

## Kapsam Dışı (bu turda YAPILMAYACAK)

- DB-tabanlı "en bayat kaynaktan başla" scheduler sıralaması (madde 2'de
  gerekçelendirildi — rotasyon yetersiz kalırsa ikinci adım).
- Fetch/analiz fazlarını ayıran kalıcı kuyruk (Kafka mesaj başına "bir
  kaynağı uçtan uca işle" modeli korunuyor — makale-granülaritesinde tam
  round-robin, mevcut trafik ölçeğinde gereksiz mühendislik).
- Batching (birden fazla makaleyi tek Groq isteğinde analiz etmek) —
  darboğazın TPM mi RPM mi olduğu netleşmeden ölçülebilir bir kazanç
  vaat etmiyor, ayrı bir spike ister.
- Düşük öncelikli kaynaklar için Groq'u tamamen atlayıp `FallbackAnalyzer`
  kullanmak — kalite tutarsızlığı riski, bu turda gerek kalmadı (havuz
  bölme + near-dup önceliği yeterli görünüyor).
- `is_duplicate` haberleri feed'den filtrelemek — ayrı bir UX kararı,
  bu spec'in kapsamı sadece Groq maliyetini/gecikmesini azaltmak.
