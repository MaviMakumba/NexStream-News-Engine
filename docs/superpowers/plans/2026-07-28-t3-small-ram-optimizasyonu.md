# t3.small RAM/Disk Optimizasyonu — Uygulama Planı

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** NexStream'in tam prod yığınını (hiçbir servis çıkarmadan) AWS `t3.small` üzerinde — 2 vCPU, 1.9GB RAM — sürekli swap'a düşmeden çalıştırmak.

**Architecture:** `app` ve `worker` container'ları SentenceTransformer modelini ayrı ayrı RAM'e yüklüyor (~600MB israf). Model yeni bir `embedder` servisine taşınır; `app`/`worker` ona `HttpEmbedderAdapter(EmbeddingPort)` üzerinden HTTP ile sorar. Böylece `torch` + `sentence-transformers` bu iki image'dan tamamen çıkar. Domain katmanı (`src/domain/`) hiç değişmez — mevcut `EmbeddingPort` soyutlaması aynen kullanılır.

**Tech Stack:** Python 3.11, FastAPI, httpx, sentence-transformers, ChromaDB (HTTP client), Docker Compose, nginx

**Spec:** `docs/superpowers/specs/2026-07-28-t3-small-ram-optimizasyonu-design.md`

**Dal:** `optimize/t3-small-ram` (spec commit'i `a068c42` burada)

## Global Constraints

- **522 mevcut backend testin tamamı her task sonunda yeşil kalmalı.** Komut: `venv\Scripts\python.exe -m pytest tests/ -v`
- Kullanıcıya görünen hiçbir özellik kaybolmayacak.
- `src/domain/` altında hiçbir dosya değişmeyecek.
- Testlerde gerçek API/ağ çağrısı yok — her şey mock (proje kuralı, CLAUDE.md).
- Yeni her modül docstring taşımalı (proje kuralı, v1.11'den beri %100 kapsam).
- Dil/metin seçimi gerekiyorsa `if lang == "TR"` zinciri YASAK — sözlük tabanlı lookup (proje kuralı).
- Import sırası: stdlib → third party → local (`src.*`).
- Env var okuma: doğrudan `os.getenv` değil, `from src.infrastructure.config.settings import settings`.
- Hedef tepe RSS: **≤ 1.6GB** (ölçüm Faz B'de; 1.9GB'a sığmak asgari şart).
- **Docker imajı değişirse `docker-compose up --build -d` gerekir** — sadece `restart` yetmez.

---

## Dosya Yapısı

### Yeni dosyalar

| Dosya | Sorumluluk |
|---|---|
| `src/adapters/search/http_embedder.py` | `HttpEmbedderAdapter(EmbeddingPort)` + `EmbeddingServiceError` — embedding'i HTTP ile uzak servise devreder |
| `src/adapters/search/embedder_factory.py` | `build_embedder()` — kompozisyon noktası, `analysis/factory.py` desenini izler |
| `src/adapters/search/embedder_service.py` | Modeli tek kopya yükleyen küçük FastAPI uygulaması (`/embed`, `/embed-batch`, `/health`) |
| `requirements-embedder.txt` | Sadece embedder image'ı: fastapi, uvicorn, sentence-transformers |
| `requirements-dev.txt` | `-r requirements.txt` + pytest (prod image'ından ayrılır) |
| `Dockerfile.embedder` | Embedder servisi image'ı (torch CPU wheel'i ile) |
| `tests/adapters/test_http_embedder.py` | Adapter + factory testleri |
| `tests/adapters/test_embedder_service.py` | Servis endpoint testleri (model mock'lu) |

### Değişen dosyalar

| Dosya | Değişiklik |
|---|---|
| `src/adapters/search/chroma_search_repository.py:10,20-21` | Modül seviyesindeki `SentenceTransformerEmbedder` import'u kaldırılır; varsayılan `build_embedder()`; tip ipucu `EmbeddingPort` |
| `src/adapters/search/sentence_transformer_embedder.py:17` | Model adı `MODEL_NAME` sabitine çıkarılır (servis `/health`'te raporlayacak) |
| `src/infrastructure/config/settings.py` | Yeni embedder ayarları |
| `src/adapters/api/routers/health_router.py` | `/health` yanıtına `embedder` alanı |
| `requirements.txt` | streamlit, plotly, sentence-transformers, pytest, pytest-asyncio çıkar; `chromadb` → `chromadb-client` |
| `requirements-light.txt` | streamlit, plotly çıkar |
| `Dockerfile` | Değişmez (artık hafif requirements kuruyor) |
| `docker-compose.yml`, `docker-compose.prod.yml` | Yeni `embedder` servisi; `app`/`worker` bağımlılığı + `EMBEDDER_URL`; chromadb healthcheck + sürüm pinleme |
| `frontend/Dockerfile` | `ENV HOSTNAME=0.0.0.0` (502 bug'ı) |
| `infra/nginx/nginx.conf` | Grafana upstream'i lazy resolver'a çevrilir |
| `.github/workflows/tests.yml:49,54` | `requirements.txt` → `requirements-dev.txt` |

---

## Task 1: Deploy'da bulunan üç bug'ın düzeltmesi

Bu üç hata 28 Temmuz 2026 canlı deploy'unda ortaya çıktı. Birbirinden bağımsız ama aynı doğrulama yöntemini (gerçek `docker compose up` + `curl`) paylaştıkları için tek task.

**Files:**
- Modify: `frontend/Dockerfile` (satır 23 civarı)
- Modify: `infra/nginx/nginx.conf` (upstream grafana + location /grafana/)
- Modify: `docker-compose.yml`, `docker-compose.prod.yml` (chromadb servisi)

**Interfaces:**
- Consumes: yok (bağımsız)
- Produces: yok (sonraki task'lar buna bağlı değil, ama deploy'un çalışması için şart)

- [ ] **Step 1: Frontend HOSTNAME düzeltmesi**

`frontend/Dockerfile`'da `ENV PORT=3000` satırının hemen ardına ekle:

```dockerfile
ENV PORT=3000
# Docker her container'a otomatik HOSTNAME=<container-id> koyar; Next.js standalone
# server.js buna bind eder ve o isim TEK bir ağ arayüzüne çözülür. Bu container iki
# ağda (frontend + backend) olduğu için nginx diğer ağdan bağlanamaz → 502.
# 28 Tem 2026 deploy'unda tam olarak bu yaşandı (nginx 172.20.0.5'e gitti,
# Next.js 172.18.0.12'de dinliyordu).
ENV HOSTNAME=0.0.0.0
```

- [ ] **Step 2: nginx grafana upstream'ini lazy çözümlemeye çevir**

`infra/nginx/nginx.conf`'ta `upstream grafana { server grafana:3000; }` bloğunu **sil**. `location /grafana/` bloğunu şuna çevir:

```nginx
        # Grafana — login formu brute-force'a karşı dar bir limitle korunur.
        # DİKKAT: proxy_pass'te DEĞİŞKEN kullanılıyor. nginx `upstream` bloklarını
        # AÇILIŞTA çözer; grafana container'ı ayakta değilse
        # "[emerg] host not found in upstream" ile nginx HİÇ açılmaz ve API dahil
        # bütün site çöker (28 Tem 2026'da yaşandı). Değişkenli proxy_pass
        # çözümlemeyi istek anına erteler → grafana ölse sadece burası 502 verir.
        location /grafana/ {
            limit_req zone=grafana burst=10 nodelay;
            resolver 127.0.0.11 valid=10s ipv6=off;
            set $grafana_upstream http://grafana:3000;
            proxy_pass $grafana_upstream/;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }
```

`127.0.0.11` Docker'ın gömülü DNS sunucusudur (tüm compose ağlarında sabittir).

- [ ] **Step 3: ChromaDB imajının içinde hangi aracın olduğunu TESPİT ET**

Mevcut healthcheck `python` çağırıyor ama imajda yok (`executable file not found in $PATH`). Neyin olduğunu varsayma, bak:

```bash
docker run --rm --entrypoint sh chromadb/chroma:1.5.5 -c 'command -v curl wget python3 python nc || echo HICBIRI'
```

- [ ] **Step 4: chromadb servisini iki compose dosyasında da düzelt**

İmajı **sürüme sabitle** (asıl kök neden `:latest`'in sessizce değişmesiydi) ve healthcheck'i Step 3'te bulunan araçla yaz. `curl` bulunduysa:

```yaml
  chromadb:
    image: chromadb/chroma:1.5.5      # :latest DEĞİL — sessiz sürüm atlamaları
                                      # healthcheck'i kırdı (28 Tem 2026)
    ...
    healthcheck:
      test: ["CMD", "curl", "-fsS", "http://localhost:8000/api/v2/heartbeat"]
      interval: 15s
      timeout: 5s
      retries: 5
      start_period: 10s
```

Step 3 `HICBIRI` derse healthcheck'i tamamen kaldır ve yerine şu yorumu bırak:

```yaml
    # healthcheck YOK: bu imajda curl/wget/python yok, container içinden HTTP
    # yoklaması yapılamıyor. `app` zaten chromadb'yi service_started ile bekliyor
    # (service_healthy DEĞİL), uygulamanın kendi /health'i chromadb'yi ayrıca
    # raporluyor — gerçek gözlemlenebilirlik orada.
```

- [ ] **Step 5: nginx config sözdizimini doğrula**

```bash
docker run --rm -v "$(pwd)/infra/nginx/nginx.conf:/etc/nginx/nginx.conf:ro" nginx:alpine nginx -t 2>&1 | tail -5
```

Beklenen: `syntax is ok` + `test is successful`.
**Not:** Bu komut ağdan bağımsız çalıştığı için `app`/`frontend` upstream'lerini çözemeyip hata verebilir. Öyleyse yalnızca **sözdizimi** satırına bak; çözümleme hatası bu aşamada normaldir.

- [ ] **Step 6: Compose dosyalarını doğrula**

```bash
docker compose -f docker-compose.yml config --quiet && echo "dev OK"
docker compose -f docker-compose.prod.yml config --quiet && echo "prod OK"
```

- [ ] **Step 7: Commit**

```bash
git add frontend/Dockerfile infra/nginx/nginx.conf docker-compose.yml docker-compose.prod.yml
git commit -m "fix: deploy'da bulunan uc altyapi bug'i

- frontend/Dockerfile: ENV HOSTNAME=0.0.0.0 — Docker'in otomatik koydugu
  HOSTNAME=<container-id> yuzunden Next.js standalone tek arayuze bind
  oluyordu, iki agli container'da nginx ulasamiyordu (her deploy'da 502)
- nginx: grafana upstream'i degiskenli proxy_pass + resolver ile lazy
  cozumlemeye cevrildi — grafana yoksa nginx HIC acilmiyor ve API dahil
  butun site cokuyordu
- chromadb: imaj surume sabitlendi (:latest sessizce degisip healthcheck'i
  kirmisti), healthcheck imajda gercekten var olan araca cevrildi"
```

---

## Task 2: Ölü bağımlılık temizliği

`streamlit` + `plotly` üç requirements dosyasında kurulu ama `src/` içinde sıfır import var (Streamlit dashboard v1.10'da silindi). Ölçülen ağırlık: streamlit 29M + pyarrow 86M + plotly 63M + altair 9.5M + pydeck 15M ≈ **203MB/image**.

**Files:**
- Modify: `requirements.txt`
- Modify: `requirements-light.txt`
- Create: `requirements-dev.txt`
- Modify: `.github/workflows/tests.yml:49,54`

**Interfaces:**
- Consumes: yok
- Produces: `requirements-dev.txt` — Task 8'de Dockerfile'lar buna göre ayarlanır

- [ ] **Step 1: Ölü olduğunu bir kez daha doğrula (varsayma)**

```bash
grep -rn "streamlit\|plotly" --include=*.py src/ tests/ ; echo "exit=$?"
```

Beklenen: hiç çıktı yok, `exit=1` (grep bulamadı). Çıktı varsa **DUR** ve raporla — silme.

- [ ] **Step 2: `requirements.txt`'ten sil**

`streamlit==1.55.0` ve `plotly==6.6.0` satırlarını sil. Ayrıca test bağımlılıklarını da çıkar: `pytest==9.0.3`, `pytest-asyncio==1.4.0`.

- [ ] **Step 3: `requirements-light.txt`'ten sil**

`streamlit==1.55.0` ve `plotly==6.6.0` satırlarını sil. Kalan dosya:

```
pydantic==2.12.5
pydantic-settings==2.14.2
python-dotenv==1.2.2
requests==2.33.0
aiokafka==0.13.0
apscheduler==3.11.2
```

- [ ] **Step 4: `requirements-dev.txt` oluştur**

```
# Geliştirme + CI bağımlılıkları. Prod image'ları bunu KURMAZ.
-r requirements.txt
pytest==9.0.3
pytest-asyncio==1.4.0
```

- [ ] **Step 5: CI'ı güncelle**

`.github/workflows/tests.yml` içinde:
- satır 49: `hashFiles('requirements.txt')` → `hashFiles('requirements-dev.txt')`
- satır 54: `pip install -r requirements.txt` → `pip install -r requirements-dev.txt`

- [ ] **Step 6: Tam test paketini çalıştır**

```bash
venv\Scripts\python.exe -m pytest tests/ -q
```

Beklenen: 522 passed. Kırılan varsa streamlit/plotly'ye gizli bir bağımlılık var demektir — raporla.

- [ ] **Step 7: Commit**

```bash
git add requirements.txt requirements-light.txt requirements-dev.txt .github/workflows/tests.yml
git commit -m "chore: olu bagimliliklari kaldir (streamlit, plotly) + test deps ayir

streamlit+plotly uc requirements dosyasinda kuruluydu ama src/'de sifir
import var — Streamlit dashboard v1.10'da silinmisti. Olculen agirlik
~203MB/image (streamlit 29M + pyarrow 86M + plotly 63M + altair 9.5M +
pydeck 15M).

pytest/pytest-asyncio prod image'indan requirements-dev.txt'ye tasindi;
CI artik onu kuruyor."
```

---

## Task 3: `chromadb` → `chromadb-client` geçişi

Kod yalnızca `chromadb.HttpClient` kullanıyor (`chroma_search_repository.py:22`, `health_router.py:29`), ama tam sunucu paketi kurulu — onnxruntime, tokenizers, opentelemetry, kubernetes client vb. hepsi geliyor.

**Files:**
- Modify: `requirements.txt`

**Interfaces:**
- Consumes: Task 2'nin temizlenmiş `requirements.txt`'i
- Produces: yok

- [ ] **Step 1: Kullanılan API yüzeyini çıkar**

```bash
grep -rn "self\.collection\.\|self\.client\.\|chromadb\." --include=*.py src/ | sort -u
```

Beklenen yüzey: `HttpClient`, `get_or_create_collection`, `upsert`, `query`, `count`, `delete`, `list_collections`/`heartbeat` (health router).

- [ ] **Step 2: `requirements.txt`'te paketi değiştir**

`chromadb==1.5.5` → `chromadb-client==1.5.5`

- [ ] **Step 3: Temiz bir sanal ortamda gerçekten çalıştığını doğrula**

**Bu adım atlanamaz** — `chromadb-client` daha dar bir API yüzeyi sunar; varsayımla ilerleme.

```bash
python -m venv /tmp/chromatest
/tmp/chromatest/Scripts/pip install chromadb-client==1.5.5
/tmp/chromatest/Scripts/python -c "import chromadb; c=chromadb.HttpClient; print('HttpClient OK')"
```

- [ ] **Step 4: Gerçek ChromaDB'ye karşı entegrasyon doğrulaması**

```bash
docker compose up -d chromadb
```

Sonra `/tmp/chromatest` ortamında:

```python
import chromadb
c = chromadb.HttpClient(host="localhost", port=8001)
col = c.get_or_create_collection("smoke_test")
col.upsert(ids=["1"], embeddings=[[0.1]*384], metadatas=[{"source":"x","published_at":"2026-01-01"}])
print("count:", col.count())
print("query:", col.query(query_embeddings=[[0.1]*384], n_results=1)["ids"])
print("where:", col.query(query_embeddings=[[0.1]*384], n_results=1, where={"source":{"$eq":"x"}})["ids"])
print("delete:", col.delete(where={"published_at": {"$lt": "2026-06-01"}}))
```

Hepsi hatasız çalışmalı — bunlar `chroma_search_repository.py`'nin kullandığı tam yüzey.

**Herhangi biri patlarsa:** `chromadb==1.5.5`'e geri dön, bu task'ı "uygulanamadı" diye işaretle ve nedenini not et. Yalnızca disk kazancı kaybedilir; **hiçbir özellik kaybolmaz**, plana devam edilir.

- [ ] **Step 5: Tam test paketi**

```bash
venv\Scripts\python.exe -m pytest tests/ -q
```

- [ ] **Step 6: Commit**

```bash
git add requirements.txt
git commit -m "chore: chromadb -> chromadb-client (sadece HttpClient kullaniliyor)

Kod yalnizca chromadb.HttpClient kullaniyor ama tam sunucu paketi
kuruluydu (onnxruntime, tokenizers, opentelemetry, kubernetes client...).
Kullanilan API yuzeyi (get_or_create_collection/upsert/query/count/delete
+ where filtreleri) gercek ChromaDB'ye karsi dogrulandi."
```

---

## Task 4: `HttpEmbedderAdapter` + `build_embedder()`

Asıl RAM kazancının temeli. `httpx` zaten `requirements.txt`'te var — yeni bağımlılık yok.

**Files:**
- Create: `src/adapters/search/http_embedder.py`
- Create: `src/adapters/search/embedder_factory.py`
- Modify: `src/adapters/search/sentence_transformer_embedder.py` (model adını sabite çıkar)
- Modify: `src/infrastructure/config/settings.py`
- Test: `tests/adapters/test_http_embedder.py`

**Interfaces:**
- Consumes: `src.domain.ports.embedding_port.EmbeddingPort` (mevcut ABC: `embed_text(str) -> list[float]`, `embed_batch(list[str]) -> list[list[float]]`)
- Produces:
  - `HttpEmbedderAdapter(base_url: str = None)` — `EmbeddingPort` implementasyonu
  - `EmbeddingServiceError(RuntimeError)`
  - `build_embedder() -> EmbeddingPort`
  - `MODEL_NAME: str` (`sentence_transformer_embedder` modülünde)
  - Yeni ayarlar: `settings.embedder_mode`, `embedder_url`, `embedder_connect_timeout`, `embedder_read_timeout`, `embedder_batch_read_timeout`, `embedder_retries`

- [ ] **Step 1: Ayarları ekle**

`src/infrastructure/config/settings.py` içinde `chroma_port` satırının ardına:

```python
    # ─── Embedder servisi (v2.0 RAM optimizasyonu) ──────────────────────────
    # Model app/worker içinde DEĞİL, ayrı bir serviste tek kopya durur.
    # "local" mod modeli süreç içine yükler — yalnızca Docker'sız geliştirme için.
    embedder_mode: str = "http"                    # "http" | "local"
    embedder_url: str = "http://embedder:8000"
    embedder_connect_timeout: float = 2.0          # aynı Docker ağı; aşılıyorsa servis yok
    embedder_read_timeout: float = 5.0             # tek embedding CPU'da ~10-30ms
    embedder_batch_read_timeout: float = 30.0      # toplu indeksleme partileri
    embedder_retries: int = 1                      # toplam 2 deneme — asılı servis
                                                   # worker döngüsünü uzun bloklamamalı
```

- [ ] **Step 2: Failing test yaz**

`tests/adapters/test_http_embedder.py`:

```python
"""HttpEmbedderAdapter ve build_embedder() testleri — gerçek ağ çağrısı YOK."""

from unittest.mock import MagicMock, patch

import httpx
import pytest

from src.adapters.search.http_embedder import EmbeddingServiceError, HttpEmbedderAdapter


def _response(payload: dict) -> MagicMock:
    resp = MagicMock()
    resp.json.return_value = payload
    resp.raise_for_status.return_value = None
    return resp


def test_embed_text_vektoru_dondurur():
    adapter = HttpEmbedderAdapter(base_url="http://embedder:8000")
    with patch("httpx.post", return_value=_response({"vector": [0.1, 0.2, 0.3]})) as mock_post:
        assert adapter.embed_text("merhaba") == [0.1, 0.2, 0.3]
    assert mock_post.call_args[0][0] == "http://embedder:8000/embed"
    assert mock_post.call_args[1]["json"] == {"text": "merhaba"}


def test_embed_batch_vektor_listesi_dondurur():
    adapter = HttpEmbedderAdapter(base_url="http://embedder:8000")
    with patch("httpx.post", return_value=_response({"vectors": [[0.1], [0.2]]})) as mock_post:
        assert adapter.embed_batch(["a", "b"]) == [[0.1], [0.2]]
    assert mock_post.call_args[0][0] == "http://embedder:8000/embed-batch"


def test_servis_erisilemezse_EmbeddingServiceError_firlatir():
    adapter = HttpEmbedderAdapter(base_url="http://embedder:8000")
    with patch("httpx.post", side_effect=httpx.ConnectError("baglanti yok")):
        with pytest.raises(EmbeddingServiceError):
            adapter.embed_text("merhaba")


def test_gecici_hatada_yeniden_dener():
    adapter = HttpEmbedderAdapter(base_url="http://embedder:8000", retries=1)
    calls = [httpx.ConnectError("gecici"), _response({"vector": [0.5]})]
    with patch("httpx.post", side_effect=calls) as mock_post:
        assert adapter.embed_text("merhaba") == [0.5]
    assert mock_post.call_count == 2


def test_build_embedder_http_modunda_http_adapter_dondurur():
    from src.adapters.search.embedder_factory import build_embedder
    with patch("src.adapters.search.embedder_factory.settings") as ms:
        ms.embedder_mode = "http"
        assert isinstance(build_embedder(), HttpEmbedderAdapter)


def test_build_embedder_local_modunda_sentence_transformer_dondurur():
    """local mod importu FONKSIYON ICINDE olmali — app/worker image'larinda
    sentence-transformers KURULU DEGIL, modul seviyesinde import edilirse
    o image'lar acilista coker."""
    from src.adapters.search import embedder_factory
    fake = MagicMock()
    with patch("src.adapters.search.embedder_factory.settings") as ms:
        ms.embedder_mode = "local"
        with patch.dict(
            "sys.modules",
            {"src.adapters.search.sentence_transformer_embedder": MagicMock(
                SentenceTransformerEmbedder=MagicMock(return_value=fake))},
        ):
            assert embedder_factory.build_embedder() is fake
```

- [ ] **Step 3: Testin başarısız olduğunu doğrula**

```bash
venv\Scripts\python.exe -m pytest tests/adapters/test_http_embedder.py -v
```

Beklenen: FAIL — `ModuleNotFoundError: No module named 'src.adapters.search.http_embedder'`

- [ ] **Step 4: `http_embedder.py`'yi yaz**

```python
"""HTTP tabanlı embedding adapter'ı — modeli ayrı bir serviste tutar.

`app` ve `worker` container'ları torch/sentence-transformers KURMAZ; embedding
işini `embedder` servisine devrederler. Böylece model RAM'de tek kopya durur
(t3.small'da iki kopya ~600MB israftı — bkz.
docs/superpowers/specs/2026-07-28-t3-small-ram-optimizasyonu-design.md).

Hata halinde `EmbeddingServiceError` fırlatır. Çağıranlar
(`ChromaSearchRepository`) bunu zaten yakalayıp güvenli varsayılana düşüyor:
arama boş liste (hybrid_search keyword'e düşer), indeksleme False, dedup
"kopya değil". Yani servis düşse de uygulama çalışmaya devam eder.
"""

import logging

import httpx

from src.domain.ports.embedding_port import EmbeddingPort
from src.infrastructure.config.settings import settings

logger = logging.getLogger(__name__)


class EmbeddingServiceError(RuntimeError):
    """Embedder servisine ulaşılamadı ya da geçersiz yanıt döndü."""


class HttpEmbedderAdapter(EmbeddingPort):

    def __init__(
        self,
        base_url: str = None,
        connect_timeout: float = None,
        read_timeout: float = None,
        batch_read_timeout: float = None,
        retries: int = None,
    ):
        self._base_url = (base_url or settings.embedder_url).rstrip("/")
        self._connect_timeout = connect_timeout or settings.embedder_connect_timeout
        self._read_timeout = read_timeout or settings.embedder_read_timeout
        self._batch_read_timeout = batch_read_timeout or settings.embedder_batch_read_timeout
        self._retries = settings.embedder_retries if retries is None else retries

    def embed_text(self, text: str) -> list[float]:
        return self._post("/embed", {"text": text}, self._read_timeout)["vector"]

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        return self._post("/embed-batch", {"texts": texts}, self._batch_read_timeout)["vectors"]

    def _post(self, path: str, payload: dict, read_timeout: float) -> dict:
        """Retry'lı POST. Tüm denemeler tükenirse EmbeddingServiceError fırlatır."""
        timeout = httpx.Timeout(read_timeout, connect=self._connect_timeout)
        last_error = None
        for attempt in range(self._retries + 1):
            try:
                response = httpx.post(f"{self._base_url}{path}", json=payload, timeout=timeout)
                response.raise_for_status()
                return response.json()
            except Exception as e:
                last_error = e
                logger.warning(
                    "Embedder isteği başarısız (deneme %d/%d): %s",
                    attempt + 1, self._retries + 1, e,
                )
        raise EmbeddingServiceError(f"Embedder servisi yanıt vermedi: {last_error}")
```

- [ ] **Step 5: `embedder_factory.py`'yi yaz**

```python
"""Embedder kompozisyon noktası — `analysis/factory.py` desenini izler.

Varsayılan `http`: model ayrı serviste, tek kopya. `local` yalnızca Docker'sız
geliştirme içindir.

DİKKAT: `local` dalındaki import FONKSİYON İÇİNDE. `app`/`worker` image'larında
`sentence-transformers` KURULU DEĞİL — modül seviyesine taşınırsa o container'lar
açılışta ImportError ile çöker. Aynı gerekçeyle `billing_router.py::_require_stripe()`
de Stripe SDK'sını fonksiyon içinde import eder.
"""

from src.domain.ports.embedding_port import EmbeddingPort
from src.infrastructure.config.settings import settings


def build_embedder() -> EmbeddingPort:
    if settings.embedder_mode == "local":
        from src.adapters.search.sentence_transformer_embedder import SentenceTransformerEmbedder
        return SentenceTransformerEmbedder()

    from src.adapters.search.http_embedder import HttpEmbedderAdapter
    return HttpEmbedderAdapter()
```

- [ ] **Step 6: Model adını sabite çıkar**

`src/adapters/search/sentence_transformer_embedder.py`:

```python
MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2"

_model_instance: SentenceTransformer = None


def _get_model() -> SentenceTransformer:
    global _model_instance
    if _model_instance is None:
        _model_instance = SentenceTransformer(MODEL_NAME, device="cpu")
    return _model_instance
```

- [ ] **Step 7: Testleri çalıştır**

```bash
venv\Scripts\python.exe -m pytest tests/adapters/test_http_embedder.py -v
```

Beklenen: 6 passed.

- [ ] **Step 8: Tam test paketi**

```bash
venv\Scripts\python.exe -m pytest tests/ -q
```

Beklenen: 528 passed (522 + 6).

- [ ] **Step 9: Commit**

```bash
git add src/adapters/search/http_embedder.py src/adapters/search/embedder_factory.py src/adapters/search/sentence_transformer_embedder.py src/infrastructure/config/settings.py tests/adapters/test_http_embedder.py
git commit -m "feat: HttpEmbedderAdapter + build_embedder() kompozisyon noktasi

Embedding'i ayri bir servise devreden EmbeddingPort implementasyonu.
app/worker artik modeli kendi RAM'ine yuklemek zorunda kalmayacak.

local mod importu bilincli olarak fonksiyon icinde: app/worker
image'larinda sentence-transformers KURULU OLMAYACAK."
```

---

## Task 5: Embedder servisi (FastAPI)

**Files:**
- Create: `src/adapters/search/embedder_service.py`
- Test: `tests/adapters/test_embedder_service.py`

**Interfaces:**
- Consumes: `SentenceTransformerEmbedder`, `MODEL_NAME` (Task 4)
- Produces: `app` (FastAPI instance) — `POST /embed` → `{"vector": [...]}`, `POST /embed-batch` → `{"vectors": [[...]]}`, `GET /health` → `{"status": "ok", "model": "..."}`. Task 8'deki `Dockerfile.embedder` bunu `uvicorn src.adapters.search.embedder_service:app` ile çalıştırır.

- [ ] **Step 1: Failing test yaz**

`tests/adapters/test_embedder_service.py`:

```python
"""Embedder servisi endpoint testleri — gerçek model YÜKLENMEZ, mock'lanır."""

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    fake_embedder = MagicMock()
    fake_embedder.embed_text.return_value = [0.1, 0.2]
    fake_embedder.embed_batch.return_value = [[0.1, 0.2], [0.3, 0.4]]
    from src.adapters.search import embedder_service
    with patch.object(embedder_service, "_get_embedder", return_value=fake_embedder):
        with TestClient(embedder_service.app) as c:
            yield c, fake_embedder


def test_embed_vektor_dondurur(client):
    c, fake = client
    r = c.post("/embed", json={"text": "merhaba dunya"})
    assert r.status_code == 200
    assert r.json() == {"vector": [0.1, 0.2]}
    fake.embed_text.assert_called_once_with("merhaba dunya")


def test_embed_batch_vektor_listesi_dondurur(client):
    c, fake = client
    r = c.post("/embed-batch", json={"texts": ["a", "b"]})
    assert r.status_code == 200
    assert r.json() == {"vectors": [[0.1, 0.2], [0.3, 0.4]]}


def test_bos_metin_422_dondurur(client):
    c, _ = client
    assert c.post("/embed", json={"text": ""}).status_code == 422


def test_bos_batch_422_dondurur(client):
    c, _ = client
    assert c.post("/embed-batch", json={"texts": []}).status_code == 422


def test_health_model_adini_raporlar(client):
    c, _ = client
    body = c.get("/health").json()
    assert body["status"] == "ok"
    assert body["model"] == "paraphrase-multilingual-MiniLM-L12-v2"
```

- [ ] **Step 2: Testin başarısız olduğunu doğrula**

```bash
venv\Scripts\python.exe -m pytest tests/adapters/test_embedder_service.py -v
```

Beklenen: FAIL — `No module named 'src.adapters.search.embedder_service'`

- [ ] **Step 3: Servisi yaz**

```python
"""Embedding servisi — SentenceTransformer modelini TEK kopya yükleyen FastAPI app.

`app` ve `worker` container'ları modeli kendi süreçlerine yüklemek yerine bu
servise HTTP ile sorar (bkz. http_embedder.py). t3.small'da (1.9GB RAM) iki
ayrı kopya ~600MB israf ediyordu.

Çalıştırma: uvicorn src.adapters.search.embedder_service:app --host 0.0.0.0 --port 8000
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from pydantic import BaseModel, Field

from src.adapters.search.sentence_transformer_embedder import (
    MODEL_NAME,
    SentenceTransformerEmbedder,
)

logger = logging.getLogger(__name__)

_embedder: SentenceTransformerEmbedder = None


def _get_embedder() -> SentenceTransformerEmbedder:
    """Singleton — model süreç ömrü boyunca bir kez yüklenir."""
    global _embedder
    if _embedder is None:
        logger.info("SentenceTransformer modeli yükleniyor: %s", MODEL_NAME)
        _embedder = SentenceTransformerEmbedder()
        logger.info("Model yüklendi.")
    return _embedder


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Modeli açılışta yükle: ilk gerçek istek indirme/yükleme beklemesin ve
    # compose healthcheck'i model hazır olmadan "healthy" demesin.
    _get_embedder()
    yield


# docs kapalı: bu servis yalnızca iç ağdan erişilir, dışarı açılmaz.
app = FastAPI(title="NexStream Embedder", lifespan=lifespan, docs_url=None, redoc_url=None)


class EmbedRequest(BaseModel):
    text: str = Field(min_length=1, max_length=20000)


class EmbedBatchRequest(BaseModel):
    texts: list[str] = Field(min_length=1, max_length=256)


@app.post("/embed")
def embed(req: EmbedRequest) -> dict:
    """Tek metni vektöre çevirir."""
    return {"vector": _get_embedder().embed_text(req.text)}


@app.post("/embed-batch")
def embed_batch(req: EmbedBatchRequest) -> dict:
    """Metin listesini toplu olarak vektöre çevirir."""
    return {"vectors": _get_embedder().embed_batch(req.texts)}


@app.get("/health")
def health() -> dict:
    """Model yüklüyse ok — compose healthcheck'i buna bakar."""
    _get_embedder()
    return {"status": "ok", "model": MODEL_NAME}
```

- [ ] **Step 4: Testleri çalıştır**

```bash
venv\Scripts\python.exe -m pytest tests/adapters/test_embedder_service.py -v
```

Beklenen: 5 passed.

- [ ] **Step 5: Tam test paketi**

```bash
venv\Scripts\python.exe -m pytest tests/ -q
```

Beklenen: 533 passed.

- [ ] **Step 6: Commit**

```bash
git add src/adapters/search/embedder_service.py tests/adapters/test_embedder_service.py
git commit -m "feat: embedder servisi — modeli tek kopya yukleyen FastAPI app

/embed, /embed-batch, /health. Model lifespan'de acilista yuklenir ki
compose healthcheck'i model hazir olmadan healthy demesin."
```

---

## Task 6: `ChromaSearchRepository`'yi factory'ye bağla

**Planın can alıcı adımı.** `chroma_search_repository.py:10`'daki modül seviyesindeki import kaldığı sürece, `sentence-transformers` içermeyen bir image'da bu modül **import anında çöker**.

**Files:**
- Modify: `src/adapters/search/chroma_search_repository.py:10,20-21`
- Test: `tests/adapters/test_chroma_search_repository.py` (yeni test eklenir)

**Interfaces:**
- Consumes: `build_embedder()` (Task 4)
- Produces: `ChromaSearchRepository(embedder: EmbeddingPort = None)` — varsayılan artık `build_embedder()`

- [ ] **Step 1: Failing test yaz**

`tests/adapters/test_chroma_search_repository.py` dosyasının sonuna ekle:

```python
def test_varsayilan_embedder_factory_uzerinden_kurulur():
    """Varsayılan embedder build_embedder()'dan gelmeli.

    SentenceTransformerEmbedder DOĞRUDAN kurulursa app/worker image'larında
    (sentence-transformers kurulu DEĞİL) çalışma anında çöker.
    """
    fake_embedder = MagicMock()
    with patch("src.adapters.search.chroma_search_repository.build_embedder",
               return_value=fake_embedder) as mock_build:
        with patch("chromadb.HttpClient"):
            repo = ChromaSearchRepository()
    mock_build.assert_called_once()
    assert repo.embedder is fake_embedder


def test_modul_sentence_transformers_import_etmiyor():
    """chroma_search_repository, sentence_transformers'ı modül seviyesinde
    import ETMEMELİ — app/worker image'larında bu paket bulunmayacak."""
    import inspect
    from src.adapters.search import chroma_search_repository
    source = inspect.getsource(chroma_search_repository)
    assert "from src.adapters.search.sentence_transformer_embedder import" not in source
    assert "import sentence_transformers" not in source
```

Dosyanın başındaki import'larda `patch` yoksa ekle: `from unittest.mock import MagicMock, patch`

- [ ] **Step 2: Testin başarısız olduğunu doğrula**

```bash
venv\Scripts\python.exe -m pytest tests/adapters/test_chroma_search_repository.py -v -k "factory or import_etmiyor"
```

Beklenen: FAIL.

- [ ] **Step 3: Import ve varsayılanı değiştir**

`src/adapters/search/chroma_search_repository.py` satır 10'u **sil**:

```python
from src.adapters.search.sentence_transformer_embedder import SentenceTransformerEmbedder
```

Yerine ekle:

```python
from src.adapters.search.embedder_factory import build_embedder
from src.domain.ports.embedding_port import EmbeddingPort
```

Satır 20-21'i değiştir:

```python
    def __init__(self, embedder: EmbeddingPort = None):
        # Varsayılan factory'den gelir (HTTP servisi). Somut sınıf DEĞİL port
        # tip ipucu: bu sınıf hangi embedder olduğunu bilmemeli.
        self.embedder = embedder or build_embedder()
```

- [ ] **Step 4: Testleri çalıştır**

```bash
venv\Scripts\python.exe -m pytest tests/adapters/test_chroma_search_repository.py tests/adapters/test_semantic_dedup.py -v
```

Beklenen: hepsi passed (mevcut testler embedder'ı zaten enjekte ediyor, kırılmamalı).

- [ ] **Step 5: Tam test paketi**

```bash
venv\Scripts\python.exe -m pytest tests/ -q
```

Beklenen: 535 passed.

- [ ] **Step 6: Commit**

```bash
git add src/adapters/search/chroma_search_repository.py tests/adapters/test_chroma_search_repository.py
git commit -m "refactor: ChromaSearchRepository embedder'i factory'den alsin

Modul seviyesindeki SentenceTransformerEmbedder import'u kaldirildi —
app/worker image'larinda sentence-transformers KURULU OLMAYACAK, bu import
kalsaydi o container'lar acilista ImportError ile cokerdi.

Tip ipucu somut sinif yerine EmbeddingPort: bu sinif hangi embedder
oldugunu bilmemeli (hexagonal dogruluk duzeltmesi)."
```

---

## Task 7: `/health`'e embedder durumu

**Files:**
- Modify: `src/adapters/api/routers/health_router.py`
- Test: `tests/adapters/test_health_router.py`

**Interfaces:**
- Consumes: `settings.embedder_url` (Task 4)
- Produces: `/health` yanıtına `"embedder": "ok"|"down"` alanı

- [ ] **Step 1: Failing test yaz**

`tests/adapters/test_health_router.py` sonuna ekle (dosyadaki mevcut çağırma desenini birebir takip et — bu dosya handler'ı doğrudan çağırıyor ve sahte `Request` scope'u geçiyor):

```python
def test_health_embedder_ok_raporlar():
    with patch("src.adapters.api.routers.health_router._check_embedder", return_value="ok"):
        body = _call_health()
    assert body["embedder"] == "ok"


def test_health_embedder_down_ise_status_degraded():
    with patch("src.adapters.api.routers.health_router._check_embedder", return_value="down"):
        body = _call_health()
    assert body["embedder"] == "down"
    assert body["status"] != "ok"
```

`_call_health()` yardımcısı dosyada yoksa, mevcut health testinin çağırma bloğunu birebir kopyalayarak oluştur.

- [ ] **Step 2: Testin başarısız olduğunu doğrula**

```bash
venv\Scripts\python.exe -m pytest tests/adapters/test_health_router.py -v -k embedder
```

- [ ] **Step 3: `_check_embedder` ekle**

`health_router.py`'de `_check_kafka` fonksiyonunun yanına:

```python
def _check_embedder() -> str:
    """Embedder servisinin /health'ini yoklar.

    Kısa timeout: /health endpoint'i her istekte gerçek bağlantı açtığı için
    yavaş bir bağımlılık tüm health kontrolünü bekletmemeli.
    """
    try:
        response = httpx.get(f"{settings.embedder_url.rstrip('/')}/health", timeout=2.0)
        return "ok" if response.status_code == 200 else "down"
    except Exception as e:
        logger.warning("Embedder health kontrolü başarısız: %s", e)
        return "down"
```

Dosyanın başına `import httpx` ekle (yoksa).

- [ ] **Step 4: Yanıta bağla**

`health_check` içinde:

```python
    embedder_status = _check_embedder()
    all_ok = all(s == "ok" for s in [db_status, kafka_status, chroma_status, embedder_status])
```

ve yanıt sözlüğüne `"embedder": embedder_status,` satırını `"chromadb"` satırının ardına ekle.

- [ ] **Step 5: Testleri çalıştır**

```bash
venv\Scripts\python.exe -m pytest tests/adapters/test_health_router.py -v
```

- [ ] **Step 6: Tam test paketi + commit**

```bash
venv\Scripts\python.exe -m pytest tests/ -q
git add src/adapters/api/routers/health_router.py tests/adapters/test_health_router.py
git commit -m "feat: /health embedder durumunu da raporlasin

Mevcut db/kafka/chromadb raporlamasiyla tutarli."
```

---

## Task 8: Requirements ayrımı, `Dockerfile.embedder`, compose bağlantısı

Bu task'tan sonra `app`/`worker` image'larında torch **yok**.

**Files:**
- Modify: `requirements.txt` (sentence-transformers çıkar)
- Create: `requirements-embedder.txt`
- Create: `Dockerfile.embedder`
- Modify: `docker-compose.yml`, `docker-compose.prod.yml`

**Interfaces:**
- Consumes: `embedder_service:app` (Task 5), `settings.embedder_url` (Task 4)
- Produces: `embedder` compose servisi (iç ağda `http://embedder:8000`)

- [ ] **Step 1: `requirements.txt`'ten `sentence-transformers` satırını sil**

`sentence-transformers==3.3.1` satırını sil. **`httpx` KALMALI** — `HttpEmbedderAdapter` onu kullanıyor.

- [ ] **Step 2: `requirements-embedder.txt` oluştur**

```
# Embedder servisi — model SADECE bu image'da yüklenir.
# torch, Dockerfile.embedder'da CPU index'inden AYRI bir adımda kurulur
# (aşağıdaki yoruma bakın), bu yüzden burada listelenmez.
fastapi==0.139.2
uvicorn==0.41.0
sentence-transformers==3.3.1
```

- [ ] **Step 3: `Dockerfile.embedder` oluştur**

```dockerfile
# Embedder servisi — SentenceTransformer modelini tek kopya yükler.
# app/worker image'ları artık torch İÇERMEZ; embedding'i bu servise sorarlar.
FROM python:3.11-slim

WORKDIR /app
ENV PYTHONUNBUFFERED=1

# hf-xet bazı ağlarda ilk model indirmesini birkaç KB'da deterministik olarak
# tıkıyor (23 Tem 2026'da lokalde yaşandı). Klasik HTTPS indirmeye zorlar.
ENV HF_HUB_DISABLE_XET=1

# torch'u AYRI ve ÖNCE kur: PyPI'ın varsayılan Linux wheel'i CUDA build'idir ve
# nvidia-* paketleriyle birlikte GB'larca yer kaplar. Sunucuda GPU YOK.
# --index-url ile CPU wheel'i çekilir; sonraki adımda sentence-transformers
# torch'u zaten kurulu bulur ve DEĞİŞTİRMEZ.
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --retries 10 --timeout 120 \
        --index-url https://download.pytorch.org/whl/cpu torch

COPY requirements-embedder.txt .
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --retries 10 --timeout 120 -r requirements-embedder.txt

COPY src/ ./src/

# --create-home şart: SentenceTransformer model cache'ini ~/.cache/huggingface'e yazar.
RUN useradd --create-home --shell /bin/bash appuser && chown -R appuser:appuser /app
USER appuser

CMD ["uvicorn", "src.adapters.search.embedder_service:app", "--host", "0.0.0.0", "--port", "8000"]
```

- [ ] **Step 4: `docker-compose.yml`'e (dev) `embedder` servisini ekle**

```yaml
  embedder:
    build:
      context: .
      dockerfile: Dockerfile.embedder
    container_name: nexstream_embedder
    restart: unless-stopped
    environment:
      - HF_HUB_DISABLE_XET=1
    healthcheck:
      # python bu image'da MEVCUT (python:3.11-slim tabanı) — chromadb'nin
      # aksine bu healthcheck çalışır.
      test: ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8000/health', timeout=5)"]
      interval: 15s
      timeout: 10s
      retries: 20          # ilk açılışta ~470MB model indirilir
      start_period: 60s
    networks:
      - backend
```

Dev compose'da ağ tanımı yoksa `networks` bloğunu dosyanın kendi desenine uydur.

- [ ] **Step 5: Dev compose'da `app` ve `worker`'ı bağla**

Her ikisinin `environment` bloğuna:

```yaml
      - EMBEDDER_URL=http://embedder:8000
```

`depends_on` bloklarına:

```yaml
      embedder:
        condition: service_healthy
```

- [ ] **Step 6: `docker-compose.prod.yml`'e aynısını ekle**

Aynı servis, ek olarak kaynak limiti:

```yaml
    deploy:
      resources:
        limits:
          memory: 900M
          cpus: "1.0"
```

- [ ] **Step 7: Compose dosyalarını doğrula**

```bash
docker compose -f docker-compose.yml config --quiet && echo "dev OK"
docker compose -f docker-compose.prod.yml config --quiet && echo "prod OK"
```

- [ ] **Step 8: GERÇEK container'larla doğrula (bu adım atlanamaz)**

`docker compose config` sadece YAML sözdizimini kontrol eder. v1.18'de Redpanda migrasyonu böyle "doğrulanmış" sayılmış, gerçek container'lar hiç ayağa kaldırılmamış ve iki ayrı bug sonraki oturuma kalmıştı.

```bash
docker compose down
docker compose up --build -d
docker compose ps
```

Beklenenler:
- `nexstream_embedder` **healthy** (ilk açılışta model indirmesi 3-5 dk sürebilir)
- `nexstream_engine` (app) **healthy**
- `app` ve `worker` loglarında `ImportError` / `ModuleNotFoundError` **yok**

```bash
docker logs nexstream_engine --tail 30
docker logs nexstream_worker --tail 30
docker exec nexstream_engine python -c "import urllib.request;print(urllib.request.urlopen('http://localhost:8000/health',timeout=10).read().decode())"
```

`/health` çıktısında `"embedder":"ok"` görünmeli.

- [ ] **Step 9: Uçtan uca arama doğrulaması**

```bash
docker exec nexstream_engine python -c "
import urllib.request, json
req = urllib.request.Request('http://localhost:8000/news/search', method='POST',
    data=json.dumps({'query':'ekonomi','n_results':3}).encode(),
    headers={'Content-Type':'application/json'})
print(urllib.request.urlopen(req, timeout=30).read().decode()[:400])
"
```

Hata dönmemeli (sonuç boş olabilir — yeni DB'de haber yoksa normaldir).

- [ ] **Step 10: `app` image'ında torch OLMADIĞINI doğrula**

```bash
docker exec nexstream_engine python -c "import torch" 2>&1 | tail -2
docker images | grep nexstream
```

İlk komut `ModuleNotFoundError: No module named 'torch'` vermeli — **bu BAŞARI göstergesidir**. İkinci komutta `app`/`worker` image boyutlarını not al (öncesi ~5GB idi).

- [ ] **Step 11: Commit**

```bash
git add requirements.txt requirements-embedder.txt Dockerfile.embedder docker-compose.yml docker-compose.prod.yml
git commit -m "feat: embedder servisini compose'a bagla, app/worker'dan torch'u cikar

app ve worker artik sentence-transformers/torch KURMUYOR; embedding'i
embedder servisine HTTP ile soruyorlar. Model RAM'de tek kopya.

torch, Dockerfile.embedder'da CPU index'inden ayri adimda kuruluyor:
PyPI'in varsayilan Linux wheel'i CUDA build'i ve sunucuda GPU yok."
```

---

## Task 9: Bozulma (degradation) testleri — embedder düşükken

`ChromaSearchRepository` metotları zaten `try/except` ile güvenli varsayılana düşüyor ve `hybrid_search` docstring'i *"Taraflardan biri hata verirse diğeri tek başına sonuç döndürür"* diyor. Bu davranış **yeniden yazılmayacak, testle kilitlenecek** — embedder artık ağ bağımlılığı olduğu için bu yol kritik hale geldi.

**Files:**
- Test: `tests/adapters/test_chroma_search_repository.py` (yeni testler)

**Interfaces:**
- Consumes: `EmbeddingServiceError` (Task 4), `ChromaSearchRepository` (Task 6)
- Produces: yok

- [ ] **Step 1: Testleri yaz**

```python
def test_embedder_olunce_arama_bos_liste_dondurur():
    """hybrid_search bunu yakalayıp keyword aramasına düşer — 500 dönmez."""
    from src.adapters.search.http_embedder import EmbeddingServiceError
    repo, embedder = make_repo()
    embedder.embed_text.side_effect = EmbeddingServiceError("servis yok")
    assert repo.search("ekonomi") == []


def test_embedder_olunce_indexleme_false_dondurur_ama_patlamaz():
    """Haber Postgres'e zaten kaydedildi; indeksleme atlanır, veri kaybı yok.
    retention_job son 7 günü yeniden indeksleyerek boşluğu kendiliğinden kapatır."""
    from src.adapters.search.http_embedder import EmbeddingServiceError
    from src.domain.models.article import Article
    repo, embedder = make_repo()
    embedder.embed_text.side_effect = EmbeddingServiceError("servis yok")
    article = Article(id=1, title="Baslik", content="icerik", url="http://x", source="TRT")
    assert repo.index_article(article) is False


def test_embedder_olunce_dedup_fail_open_davranir():
    """Kopya olmadığı varsayılır — en kötü ihtimalle bir kopya haber geçer,
    ki bu haberi tamamen kaybetmekten iyidir."""
    from src.adapters.search.http_embedder import EmbeddingServiceError
    from src.domain.models.article import Article
    repo, embedder = make_repo()
    repo.collection.count.return_value = 5
    embedder.embed_text.side_effect = EmbeddingServiceError("servis yok")
    article = Article(id=1, title="Baslik", content="icerik", url="http://x", source="TRT")
    assert repo.is_near_duplicate(article) is False
```

`Article(...)` çağrısındaki zorunlu alanları dosyadaki mevcut testlerden birebir kopyala — model imzası farklıysa ona uydur.

- [ ] **Step 2: Testleri çalıştır**

```bash
venv\Scripts\python.exe -m pytest tests/adapters/test_chroma_search_repository.py -v -k "olunce"
```

Beklenen: 3 passed (mevcut `try/except`'ler sayesinde implementasyon değişikliği gerekmemeli). **FAIL olursa** ilgili metoda `except` bloğu eklenmesi gerekir — o zaman ekle ve tekrar çalıştır.

- [ ] **Step 3: Tam test paketi + commit**

```bash
venv\Scripts\python.exe -m pytest tests/ -q
git add tests/adapters/test_chroma_search_repository.py
git commit -m "test: embedder erisilemezken bozulma davranisini kilitle

Embedder artik ag bagimliligi; arama keyword'e dusuyor, indeksleme
atlaniyor (veri kaybi yok), dedup fail-open. Davranis zaten vardi,
regresyona karsi testle sabitlendi."
```

---

## Task 10: Faz B — Gerçek bellek ölçümü

Bundan sonrası tahminle değil sayıyla ilerler.

**Files:**
- Modify: `docs/superpowers/specs/2026-07-28-t3-small-ram-optimizasyonu-design.md` (ölçüm sonuçları eklenir)

**Interfaces:**
- Consumes: Task 8'in çalışan yığını
- Produces: Faz C kararı için ölçüm tablosu

- [ ] **Step 1: Tam yığını temiz başlat**

```bash
docker compose down
docker compose up --build -d
docker compose ps
```

Tüm container'lar sağlıklı olana kadar bekle (embedder ilk açılışta 3-5 dk).

- [ ] **Step 2: Yığın oturana kadar bekle, sonra ölç**

Container'lar healthy olduktan **sonra en az 5 dakika** bekle (worker bir scrape döngüsü tamamlasın, bellek gerçek çalışma seviyesine otursun), sonra:

```bash
docker stats --no-stream --format "table {{.Name}}\t{{.MemUsage}}\t{{.MemPerc}}"
```

- [ ] **Step 3: Toplamı hesapla**

```bash
docker stats --no-stream --format "{{.MemUsage}}" | awk -F'/' '{print $1}' | sed 's/MiB//;s/GiB/*1024/' | bc | paste -sd+ | bc
```

(Windows'ta `bc` yoksa değerleri elle topla.)

- [ ] **Step 4: Sonuçları spec'e yaz**

Spec'in "6.1 Bütçe projeksiyonu" bölümünün altına gerçek tabloyu ekle:

```markdown
### 6.2 Faz B — ÖLÇÜLEN sonuçlar (<tarih>)

| Container | Ölçülen RSS |
|---|---|
| ... | ... |
| **TOPLAM** | **... MiB** |

**Karar:** [≤1.6GB ise "Faz C gerekmiyor" / değilse "Faz C madde X'ten devam"]
```

- [ ] **Step 5: Commit**

```bash
git add docs/superpowers/specs/2026-07-28-t3-small-ram-optimizasyonu-design.md
git commit -m "docs: Faz B bellek olcum sonuclari"
```

---

## Task 11: Faz C — Koşullu kısma

**Yalnızca Task 10 toplamı 1.6GB'ı aşarsa yapılır.** Maddeler **sırayla** uygulanır, her maddeden sonra yeniden ölçülür; hedefe ulaşıldığında kalan maddeler **yapılmaz**.

**Files:**
- Modify: `docker-compose.prod.yml` (madde 1, 3), `Dockerfile.embedder` (madde 2), `infra/prometheus/prometheus.yml` + `infra/loki/loki-config.yml` (madde 3)

**Interfaces:**
- Consumes: Task 10'un ölçüm tablosu
- Produces: yok

- [ ] **Madde 1: Redpanda heap 512M → 256M** (tahmini ~256MB, ödün yok)

`docker-compose.prod.yml`'de `- --memory=512M` → `- --memory=256M`.
Container limitini (`memory: 768M`) **değiştirme** — heap ile limit eşitlenirse Seastar açılamaz (28 Tem 2026'da `insufficient physical memory: needed 805306368 available 759169024` hatası tam olarak buydu).

Sonra: `docker compose -f docker-compose.prod.yml up -d redpanda` → healthy olduğunu doğrula → yeniden ölç.

- [ ] **Madde 2: Torch thread havuzlarını kıs** (tahmini ~50-100MB, ödün yok)

`Dockerfile.embedder`'a `ENV HF_HUB_DISABLE_XET=1` satırının ardına:

```dockerfile
# 2 vCPU'da torch'un thread havuzu zaten çekişiyordu; tek thread hem RAM
# hem context-switch tasarrufu sağlar. Tek cümlelik embedding ~10-30ms.
ENV OMP_NUM_THREADS=1
ENV MKL_NUM_THREADS=1
```

Sonra `docker compose up --build -d embedder` → yeniden ölç.

- [ ] **Madde 3: Monitoring retention 30 gün → 7 gün** (tahmini ~150-250MB, **küçük ama gerçek ödün**)

`docker-compose.prod.yml`'de prometheus komutundaki `--storage.tsdb.retention.time=30d` → `=7d`; ayrıca `--storage.tsdb.retention.size=512MB` ekle. Loki config'inde retention süresini aynı pencereye çek.

**Dört servis de çalışmaya devam eder**, tüm paneller/metrikler durur — yalnızca geriye bakış penceresi daralır. Bu ödünü CLAUDE.md'ye not düş.

Sonra yeniden ölç.

- [ ] **Madde 4: ONNX int8 — YAPMA, KULLANICIYA SOR**

Madde 1-3'ten sonra hâlâ hedefin üstündeyse **DUR**. Bu madde arama kalitesinde ~%1-2 düşüşe yol açar. Ölçüm tablosunu ve iki seçeneği kullanıcıya sun:

1. ONNX int8'e geçiş → ~370MB kazanç, ~%1-2 arama kalitesi ödünü, para maliyeti yok
2. `t3.medium`'a yükseltme → kalite ödünü yok, kredi ömrü ~3.5 aydan ~2.2 aya iner

**Kullanıcı onayı olmadan hiçbirini uygulama.**

- [ ] **Son adım: Commit**

```bash
git add -A
git commit -m "perf: Faz C — <uygulanan maddeler> ile bellek kullanimini dusur"
```

---

## Task 12: Dokümantasyon ve kapanış

**Files:**
- Modify: `CLAUDE.md`
- Modify: `DEPLOY.md`
- Modify: `README.md`

- [ ] **Step 1: `CLAUDE.md`'yi güncelle**

- Mimari ağacına `embedder_service.py`, `http_embedder.py`, `embedder_factory.py` eklensin
- Docker servis tablolarına `embedder` satırı eklensin
- Yeni env var'lar listesine: `EMBEDDER_MODE`, `EMBEDDER_URL`, `EMBEDDER_CONNECT_TIMEOUT`, `EMBEDDER_READ_TIMEOUT`, `EMBEDDER_BATCH_READ_TIMEOUT`, `EMBEDDER_RETRIES`
- "BİLİNEN NOTLAR"a üç bug'ın kalıcı dersleri:
  - Next.js standalone + Docker'ın otomatik `HOSTNAME`'i → çok ağlı container'da 502
  - nginx `upstream` bloklarını açılışta çözer → tek eksik upstream tüm siteyi düşürür; opsiyonel olanlar değişkenli `proxy_pass` + `resolver` ile lazy olmalı
  - Docker image'larını `:latest` ile kullanma → sessiz sürüm atlaması healthcheck kırar
- Test sayısını güncelle

- [ ] **Step 2: `DEPLOY.md`'yi güncelle**

AWS köprü deploy'u için: yeni `embedder` servisi, ilk açılışta model indirme süresi, `EMBEDDER_URL`, ve t3.small'da swap dosyası oluşturma adımı (bu deploy'da gerekmişti).

- [ ] **Step 3: `README.md`'yi güncelle**

Mimari diyagramına `embedder` servisini ekle.

- [ ] **Step 4: Commit ve PR**

```bash
git add CLAUDE.md DEPLOY.md README.md
git commit -m "docs: embedder servisi + t3.small optimizasyonu dokumantasyonu"
git push -u origin optimize/t3-small-ram
```

---

## Self-Review Notları

**Spec kapsamı:** Spec §4.1 → Task 2; §4.2 → Task 8 Step 3; §4.3 → Task 3; §4.4 → Task 4-6, 8; §5 → Task 10; §6 → Task 11; §7 (üç bug) → Task 1; §8 → Task 4 (timeout'lar) + Task 7 (health) + Task 9 (bozulma); §9 → Task 4, 5, 6, 9. Kapsanmayan bölüm yok.

**Bilinçli riskler ve karşılıkları:**
- `chromadb-client` yetersiz kalabilir → Task 3 Step 4 gerçek ChromaDB'ye karşı doğrular, yetmezse geri dönüş yolu tanımlı
- torch CPU kurulumu sözdizimi → Task 8 Step 3'te `--index-url` ile ayrı adım (en dayanıklı biçim), Step 10'da `import torch` başarısızlığıyla doğrulanır
- Modül seviyesindeki import'un kaçması → Task 6 Step 1'de kaynak kodu denetleyen özel test (`test_modul_sentence_transformers_import_etmiyor`) + Task 8 Step 8'de gerçek container doğrulaması
