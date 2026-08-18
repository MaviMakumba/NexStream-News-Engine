# NexStream — t3.small (2GB RAM) RAM/Disk Optimizasyonu — Tasarım

**Tarih:** 28 Temmuz 2026
**Durum:** Onaylandı, uygulama planı bekleniyor
**Bağlam:** v2.0 AWS köprü deploy'u (bkz. `DEPLOY.md`, CLAUDE.md "AWS köprüsü")

---

## 1. Problem

NexStream'in tam prod yığını (15 container) AWS `t3.small` üzerinde (2 vCPU, **1.9GB kullanılabilir RAM**, x86_64) ayağa kalkıyor ama **sürekli swap'a düşüyor**.

Canlıda ölçülen gerçek kullanım:

```
Mem:   1.9Gi total   1.3Gi used   ~108Mi free
Swap:  2.0Gi total   1.7Gi used
→ toplam gerçek talep ≈ 3.0GB
```

Bu yığın Oracle Cloud Always Free ARM makinesine (4 vCPU / 24GB) göre tasarlanmıştı. Oracle'da `VM.Standard.A1.Flex` kapasitesi sürekli "Out of host capacity" verdiği için AWS'e köprü kuruldu; hedef makine 10× daha küçük.

**Kısıt (kullanıcı kararı):** Hiçbir servis yığından çıkarılmayacak. Monitoring (Prometheus + Grafana + Loki + Promtail) dahil her şey çalışmaya devam edecek. Çözüm, servis silmek değil, **kodu ve paketleri makineye sığdırmak**.

## 2. Hedef ve başarı kriteri

- Tam yığın (15 → 16 container) 1.9GB RAM'de, swap'a **sürekli** yaslanmadan çalışsın
- Hedef tepe RSS: **≤ 1.6GB** (kalan ~300MB işletim sistemi + tampon; swap acil durum yastığı olarak kalsın, normal çalışma modu olmasın)
- **522 backend testin tamamı yeşil kalsın**
- Kullanıcıya görünen hiçbir özellik kaybolmasın
- Domain katmanı (`src/domain/`) değişmesin

## 3. Kök neden analizi (ölçülmüş)

| # | Bulgu | Doğrulama | Kazanç türü |
|---|---|---|---|
| 1 | `streamlit` + `plotly` üç requirements dosyasında kurulu, `src/`'de sıfır import | `dashboard/` klasörü yok (v1.10'da silindi); `grep` sadece `_archive/` içinde buldu | **Disk** ~203MB/image (streamlit 29M + pyarrow 86M + plotly 63M + altair 9.5M + pydeck 15M) |
| 2 | Linux'ta `torch` varsayılan wheel'i CUDA build'i; sunucuda GPU yok | Windows venv'de CPU build 479MB; Linux CUDA build'i `nvidia-*` paketleriyle birlikte belirgin şekilde daha büyük — **uygulama sırasında gerçek image üzerinde doğrulanacak** | **Disk**, RAM'e etkisi sınırlı |
| 3 | Tam `chromadb` sunucu paketi kurulu, ama kod sadece `chromadb.HttpClient` kullanıyor | `chroma_search_repository.py:22` | **Disk** (onnxruntime, tokenizers, opentelemetry, kubernetes client vb. gereksiz) |
| 4 | **`app` ve `worker` SentenceTransformer modelini AYRI AYRI RAM'e yüklüyor** | İkisi de aynı `Dockerfile`'ı kullanıyor; ikisi de `ChromaSearchRepository` üzerinden embedder kuruyor | **RAM ~600MB** ← asıl mesele |

**Sonuç:** 1-2-3 disk ve build süresi kazandırır ama RAM sorununu çözmez. Asıl RAM kazancı 4. maddeden gelir.

## 4. Faz A — Yapısal değişiklikler

### 4.1 Ölü bağımlılık temizliği

- `requirements.txt`: `streamlit`, `plotly` **silinir**
- `requirements-light.txt`: `streamlit`, `plotly` **silinir**
- `pytest`, `pytest-asyncio` prod image'ından ayrılır → yeni `requirements-dev.txt`
  (CI `python -m pytest` çalıştırdığı için CI workflow'u bu dosyayı da kuracak şekilde güncellenir)

### 4.2 torch → CPU wheel

Yalnızca embedder image'ında torch kalacak; orada CPU wheel'ine sabitlenir:

```
--extra-index-url https://download.pytorch.org/whl/cpu
torch==<sürüm>+cpu
```

`+cpu` yerel sürüm etiketi yalnızca Linux'ta mevcut; bu dosya sadece Docker (Linux) build'inde kullanıldığı için sorun değil. Kesin sürüm/sözdizimi uygulama sırasında doğrulanacak.

### 4.3 `chromadb` → `chromadb-client`

Kod yalnızca `HttpClient` kullandığı için hafif client paketi yeterli olmalı.

**Doğrulama şartı:** `chromadb-client`'ın kullandığımız tüm API yüzeyini (koleksiyon oluşturma, `add`, `query`, metadata filtreleri, `delete`) karşıladığı uygulama sırasında test edilerek doğrulanacak. Karşılamıyorsa tam pakette kalınır — bu durumda yalnızca disk kazancı kaybedilir, **hiçbir özellik kaybolmaz**.

### 4.4 Embedding servisi (asıl RAM kazancı)

#### Mimari

```
                    ┌──────────────┐
      app ─────────►│              │
   (FastAPI)        │   embedder   │  ← modeli TEK kopya yükler
                    │  (FastAPI)   │     (torch + sentence-transformers
      worker ──────►│              │      SADECE bu image'da)
   (consumer)       └──────────────┘
```

`app` ve `worker` image'larından `torch` ve `sentence-transformers` **tamamen çıkar**.

#### Yeni dosyalar

| Dosya | Sorumluluk |
|---|---|
| `src/adapters/search/embedder_service.py` | Küçük FastAPI uygulaması. `POST /embed`, `POST /embed-batch`, `GET /health`. Modeli süreç ömrü boyunca tek kez yükler. |
| `src/adapters/search/http_embedder.py` | `HttpEmbedderAdapter(EmbeddingPort)` — `embed_text`/`embed_batch`'i HTTP üzerinden çağırır. |
| `src/adapters/search/embedder_factory.py` | `build_embedder()` — kompozisyon noktası. `adapters/analysis/factory.py::build_analyzer()` desenini birebir izler. |
| `requirements-embedder.txt` | fastapi, uvicorn, sentence-transformers, torch (CPU) |
| `Dockerfile.embedder` | Yalnızca embedder servisi için image |

#### Değişen dosyalar

| Dosya | Değişiklik | Neden kritik |
|---|---|---|
| `src/adapters/search/chroma_search_repository.py` | Satır 10'daki **modül seviyesindeki** `SentenceTransformerEmbedder` import'u kaldırılır; varsayılan `build_embedder()` olur (fonksiyon içi/lazy import). Satır 20'deki tip ipucu `SentenceTransformerEmbedder` → `EmbeddingPort`. | **Tasarımın can alıcı noktası.** Bu import modül seviyesinde kaldığı sürece, `sentence-transformers` içermeyen bir image'da modül **import anında çöker**. Tip ipucunun port'a çevrilmesi ayrıca hexagonal doğruluk düzeltmesidir. |
| `src/dependencies.py` | Embedder'ı `build_embedder()` ile kurar | Kompozisyon noktası |
| `src/adapters/messaging/kafka_consumer.py` | Aynı | Kompozisyon noktası |
| `src/infrastructure/config/settings.py` | Yeni: `embedder_mode` (`http`\|`local`), `embedder_url`, `embedder_timeout_seconds` | `local` mod dev/test için korunur — mevcut davranışa geri dönüş yolu |
| `docker-compose.yml`, `docker-compose.prod.yml` | Yeni `embedder` servisi + healthcheck; `app`/`worker` → `depends_on: embedder` | |

**Lazy import deseni:** Proje bu deseni zaten kullanıyor — `billing_router.py::_require_stripe()` Stripe SDK'sını fonksiyon içinde import ediyor. Aynı gerekçe (paket kurulu olmayabilir / açılışı yavaşlatmasın) burada da geçerli.

#### Yan kazanç

Şu an `app` **ve** `worker` model dosyasını (~470MB) ayrı ayrı indiriyor — canlıda ilk açılışın 3-5 dakika sürmesinin sebebi bu. Bundan sonra yalnızca `embedder` indirir.

## 5. Faz B — Ölçüm

Faz A tamamlandıktan sonra, tahminle değil ölçümle devam edilir:

- Lokalde tam yığın ayağa kaldırılır, `docker stats --no-stream` ile her container'ın gerçek RSS'i kaydedilir
- Toplam ≤ 1.6GB ise Faz C atlanır
- Değilse Faz C sırayla uygulanır ve her adımdan sonra yeniden ölçülür

Ölçüm sonuçları bu dokümana ek olarak kaydedilir.

## 6. Faz C — Koşullu kısma (yalnızca ölçüm gerektirirse, bu sırayla)

| Sıra | Değişiklik | Tahmini kazanç | Ödün |
|---|---|---|---|
| 1 | Redpanda heap 512M → 256M | ~256MB | **Yok.** Düşen tavan saniyede binlerce mesajda anlam taşır; bu boru hattı 10 dakikada bir avuç mesaj işliyor |
| 2 | `OMP_NUM_THREADS=1`, `MKL_NUM_THREADS=1` (embedder) | ~50-100MB | **Yok.** 2 vCPU'da torch'un thread havuzu zaten çekişiyordu |
| 3 | Monitoring retention 30 gün → 7 gün | ~150-250MB | **Küçük ama gerçek:** 4 servis de çalışır, tüm paneller/metrikler durur, yalnızca geriye bakış penceresi daralır. Tek satır config, geri alınabilir |
| 4 | Embedder → ONNX int8 | ~370MB | **Gerçek kalite ödünü:** quantization vektörleri değiştirir, retrieval kalitesi tipik olarak %1-2 düşer. **Varsayılan olarak YAPILMAZ.** Sıra buraya gelirse önce ölçüm yapılıp kullanıcıya rakamla sunulur |

### 6.1 Bütçe projeksiyonu — dürüst aritmetik

Kaba tahminler (ölçülen 3.0GB'a kalibre edilmiş), Faz B bunları gerçek sayılarla değiştirecek:

| Aşama | Tahmini toplam | 1.9GB'a sığar mı? | 1.6GB hedefine ulaşır mı? |
|---|---|---|---|
| Bugün | ~3.0GB | ❌ (swap'ta yüzüyor) | ❌ |
| Faz A sonrası | ~2.4GB | ❌ | ❌ |
| + Faz C 1-2 (redpanda, thread) | ~2.1GB | sınırda | ❌ |
| + Faz C 3 (retention) | ~1.9GB | ✅ ucu ucuna | ❌ |
| + Faz C 4 (ONNX int8) | ~1.5GB | ✅ rahat | ✅ |

**Bu tablonun açıkça söylediği şey:** Faz A tek başına yetmez ve **1.6GB hedefine kaliteye dokunmadan ulaşmak muhtemelen mümkün değil.** Gerçekçi sonuç, Faz C 1-3'ten sonra ~1.9GB'a "ucu ucuna" sığmaktır — çalışır ama tamponu dardır.

**Bu yüzden ölçüm (Faz B) kritik:** tahminler gerçeğe göre kayabilir, karar sayıyla verilecek.

**Eşik aşılırsa iki seçenek — ikisi de kullanıcı kararı, sessizce yapılmaz:**
1. Faz C madde 4 (ONNX int8) → ~%1-2 arama kalitesi ödünü, para maliyeti yok
2. `t3.medium`'a çıkmak → kalite ödünü yok, kredi ömrü ~3.5 aydan ~2.2 aya iner

### 6.2 Faz B — ÖLÇÜLEN sonuçlar (29 Temmuz 2026, lokal dev yığını)

Faz A tamamlandıktan sonra, tüm container'lar healthy olduktan ~5 dk sonra
`docker stats --no-stream` ile ölçüldü (Docker Desktop / Windows, 6.6GB'lık VM —
yani hiçbir servis bellek baskısı altında değil, sayılar "rahat koşulda gerçek
kullanım"ı gösteriyor).

| Container | Ölçülen RSS | Not |
|---|---|---|
| embedder | **719,6 MiB** | torch CPU + model, tek kopya |
| redpanda | 189,8 MiB | dev heap `--memory=512M` |
| frontend | 154,1 MiB | **dev server** — prod standalone build daha küçük |
| app (engine) | **132,1 MiB** | önceden modeli kendi yüklüyordu |
| worker | **96,3 MiB** | önceden modeli kendi yüklüyordu |
| db | 42,6 MiB | |
| chromadb | 37,0 MiB | |
| scheduler | 29,0 MiB | |
| adminer | 9,5 MiB | sadece dev, prod'da YOK |
| redis | 7,4 MiB | |
| **TOPLAM (dev)** | **~1,38 GiB** | |

**Asıl kazanç burada görünüyor:** app + worker birlikte **228 MiB**. Bu ikisi
daha önce modeli AYRI AYRI yüklüyordu; embedder'ın tek kopyası 720 MiB olduğuna
göre, önceki durumda bu iki container'ın tek başına ~1,4 GiB civarında olduğu
anlaşılıyor. İkinci gözlemlenebilir kanıt: `nexstream_engine` artık **6 saniyede**
healthy oluyor (önceden model yüklemesi yüzünden 1-2 dakika sürüyordu).

**Ama dev yığını prod DEĞİL.** Prod'da ek olarak nginx, certbot, prometheus,
grafana, loki, promtail, backup var (~500-600 MiB) ve `app` iki uvicorn worker'ı
ile çalışıyor; buna karşılık adminer yok ve frontend standalone (daha küçük).
Dürüst projeksiyon: **~1,9-2,0 GiB** → t3.small'ın 1,9GB'ına **sığmıyor ya da
ucu ucuna sığıyor.**

**Karar: Faz C madde 1-3 uygulanacak.** Üçü de kullanıcıya görünen hiçbir
özelliği kaldırmıyor (madde 3 yalnızca metrik geçmişinin penceresini daraltıyor).
Madde 4 (ONNX int8) uygulanmayacak — kullanıcı onayı gerektiriyor ve madde 1-3
sonrası muhtemelen gerekmeyecek.

**Nihai/otoriter ölçüm t3.small'ın kendisinde yapılacak** (Task 13): farklı
çekirdek, farklı yük, gerçek prod compose. Yukarıdaki dev sayıları yön verir,
son sözü söylemez.

### 6.3 Faz C — UYGULANAN maddeler (29 Temmuz 2026)

| Madde | Ne yapıldı | Ölçülen/beklenen etki | Ödün |
|---|---|---|---|
| 1 | Redpanda heap `768M` → `256M` (prod) | ~250-400 MiB | yok |
| 2 | `OMP_NUM_THREADS=1` + `MKL_NUM_THREADS=1` (embedder) | **719,6 → 633 MiB (ölçüldü, −87 MiB)** | yok |
| 3 | Prometheus retention 30g → 7g + 512MB tavan; Loki'ye 7 günlük retention + compactor | ~150-250 MiB (tahmin) | yalnızca geriye bakış penceresi |
| 4 | ONNX int8 | **UYGULANMADI** | kullanıcı onayı gerektirir |

Madde 1 uygulanırken **planda olmayan bir bug** çıktı: `docker-compose.prod.yml`'de
Redpanda heap'i (`--memory=768M`) container limitiyle (`memory: 768M`) BİREBİR
aynıydı — yani 28 Temmuz AWS deploy'unda Redpanda'yı hiç açılmaz yapan durumun ta
kendisi. O gün sunucuda elle düzeltilmiş ama repo'ya girmemişti; taze bir deploy
aynı çökmeyi tekrar üretirdi.

Madde 3'te ayrıca keşfedildi: **Loki'de hiç retention tanımlı değildi**, loglar
sonsuza kadar birikiyordu. `retention_period` tek başına yetmiyor — silmeyi
compactor yapıyor ve `retention_enabled: true` olmadan Loki süreyi yok sayıyor.

Ek olarak `app` (4G) ve `worker` (4G) bellek limitleri 1.9GB'lık bir makinede
anlamsızdı (limit fiilen yoktu); ölçüme dayanarak 768M ve 512M'ye çekildi.

**Yeni dev toplamı: ~1,30 GiB** (1,38'den).

## 7. Deploy sırasında bulunan gerçek repo bug'ları

Bunlar 28 Temmuz 2026 canlı deploy'unda ortaya çıktı ve bu işin kapsamına dahildir.

### Bug 1 — Frontend her temiz deploy'da 502 (`frontend/Dockerfile`)

Docker her container'a otomatik olarak `HOSTNAME=<container-id>` env var'ı koyar. Next.js standalone `server.js` `process.env.HOSTNAME`'e bind eder. Bu isim yalnızca **tek bir** ağ arayüzüne çözülür. `frontend` container'ı iki ağda (`frontend` + `backend`) olduğu için, nginx `frontend` ağı üzerinden bağlanmaya çalıştığında o arayüzde dinleyen kimse olmaz → **Connection refused → 502**.

Kanıt: nginx `172.20.0.5`'e bağlanmaya çalışıyordu, Next.js `172.18.0.12`'de dinliyordu.

**Düzeltme:** `frontend/Dockerfile`'a `ENV HOSTNAME=0.0.0.0`.
**Şiddet:** Her temiz deploy'da siteyi tamamen düşürür.

### Bug 2 — ChromaDB kalıcı olarak "unhealthy"

Healthcheck `["CMD", "python", "-c", ...]` kullanıyor, ancak güncel `chromadb/chroma:latest` imajında `python` PATH'te yok (`executable file not found in $PATH`). Healthcheck hiçbir zaman geçemez.

Uygulama etkilenmiyor (`app`, chromadb'yi `condition: service_started` ile bekliyor, `service_healthy` değil) — ama yanıltıcı ve ileride `service_healthy` kullanılırsa kilitlenmeye yol açar.

**Asıl ders:** İmaj `:latest` ile pinlenmemiş; imaj sessizce değişip healthcheck'i kırmış.
**Düzeltme:** İmajı belirli sürüme sabitle + imajda gerçekten bulunan bir araçla healthcheck yaz (uygulama sırasında imaj içeriği kontrol edilerek belirlenecek).

### Bug 3 — nginx, tek bir upstream yoksa hiç açılmıyor (`infra/nginx/nginx.conf`)

nginx tüm `upstream` bloklarını **açılışta** DNS'ten çözer. Biri çözülemezse nginx tamamen açılmayı reddeder:

```
[emerg] host not found in upstream "grafana:3000" in /etc/nginx/nginx.conf:67
```

Yani grafana container'ı OOM ile ölse **API dahil bütün site** çöker. RAM'i dar bir makinede OOM gerçek bir ihtimal olduğu için bu ciddi bir tek-hata-noktasıdır. 28 Temmuz'da tam olarak bu yaşandı.

**Düzeltme:** Opsiyonel upstream'ler (grafana) için Docker'ın iç DNS'ini `resolver` olarak tanımlayıp değişkenli `proxy_pass` kullan → çözümleme istek anına ertelenir. Grafana ölse yalnızca `/grafana/` 502 verir, site ayakta kalır.

## 8. Hata yönetimi

Embedder artık iki kritik yolda ağ bağımlılığı. Projenin mevcut kuralı uygulanır: *"Exception'ları yut, logla, fallback dön — servis çökmemeli"* (CLAUDE.md, Kodlama Kuralları).

| Yol | Embedder erişilemezse | Sonuç |
|---|---|---|
| Arama (`app`) | Semantik yarı atlanır, PostgreSQL keyword araması çalışır | Arama çalışır, kalitesi düşer — **500 dönmez** |
| İndeksleme (`worker`) | Haber Postgres'e kaydedilir, ChromaDB'ye yazılmaz, uyarı loglanır | **Veri kaybı yok** |
| Dedup (`is_near_duplicate`) | "Kopya değil" varsayılır (fail-open) | En kötü ihtimalle bir kopya haber geçer |

**Kaçan indekslemeler için yeni mekanizma gerekmez:** `retention_job.py` zaten her çalıştığında son 7 günün haberlerini yeniden indeksliyor (self-healing, v1.11 sonrası eklendi). Bu yol kaçanları kendiliğinden toparlar.

**Zaman aşımı (başlangıç değerleri, `settings` üzerinden ayarlanabilir):**

| Ayar | Değer | Gerekçe |
|---|---|---|
| connect timeout | 2 sn | Aynı Docker ağı; bu süre aşılıyorsa servis ayakta değildir |
| read timeout (`embed_text`) | 5 sn | Tek cümlelik embedding CPU'da ~10-30 ms; 5 sn zaten felaket senaryosu |
| read timeout (`embed_batch`) | 30 sn | Toplu indeksleme partileri daha uzun sürebilir |
| retry | 1 (yani toplam 2 deneme) | Anlık ağ hıçkırığını toparlar; asılı kalan servis için worker döngüsünü uzun süre bloklamaz |

Asılı bir embedder, worker'ın haber işleme döngüsünü bloklamamalı — bu yüzden retry sayısı bilinçli olarak düşük.

**Health raporlama:** `embedder` kendi `/health`'ini sunar (compose healthcheck buna bağlanır). `app`'in mevcut `/health` yanıtına `embedder` alanı eklenir — hâlihazırdaki `db`/`kafka`/`chromadb` raporlamasıyla tutarlı.

## 9. Test stratejisi

Proje kuralı: *"Test'lerde gerçek API çağrısı yok, her şey mock."*

- `HttpEmbedderAdapter` — HTTP mock'lu birim testler (başarı, timeout, hata yanıtı)
- Fallback davranışları — embedder ölüyken: arama keyword'e düşüyor mu, worker çökmeden devam ediyor mu, dedup fail-open mu
- `build_embedder()` — `settings.embedder_mode`'a göre doğru adapter seçimi
- `embedder_service` — `/embed`, `/embed-batch`, `/health` (model mock'lu)
- `settings` — yeni env var varsayılanları

**Regresyon riski ve azaltımı:** Mevcut testler embedder'ı zaten enjekte ediyor (`ChromaSearchRepository(embedder=mock_embedder)` — `test_chroma_search_repository.py`, `test_semantic_dedup.py`), yani ihtiyacımız olan dikiş yeri hazır. Yine de `chroma_search_repository.py`'nin varsayılan kurulumu değiştiği için **tam test paketi her adımda çalıştırılacak**.

Tahmini: **+15-20 test** (522 → ~540).

## 10. Kapsam dışı (YAGNI)

- Analyzer zinciri (`FallbackAnalyzer`, Groq/HF) — dokunulmaz
- Embedding modelinin kendisi — Faz A'da değişmez (yalnızca Faz C madde 4'te, son çare, ayrı onayla)
- Compose → K8s/başka orkestrasyon geçişi
- Frontend özellikleri, tema sistemi, i18n
- İlgisiz refactoring

## 11. Riskler

| Risk | Azaltım |
|---|---|
| `chromadb-client` kullandığımız API yüzeyini karşılamayabilir | Uygulama sırasında test edilerek doğrulanır; karşılamazsa tam pakette kalınır (yalnızca disk kaybı) |
| `torch==...+cpu` sürüm/sözdizimi sorunları | Gerçek Linux image build'inde doğrulanır |
| Faz A sonrası hâlâ 1.9GB'a sığmama | Faz C sırayla; en sonunda `t3.medium` seçeneği kullanıcıya sunulur |
| Modül seviyesindeki import'un gözden kaçması → image'da çalışma anı çökmesi | Testler + gerçek image ile lokal `docker compose up` doğrulaması (yalnızca `docker compose config` yetmez — v1.18'de bu ders alınmıştı) |
