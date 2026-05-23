# NexStream News Engine — CLAUDE.md

Bu dosya Claude Code için proje bağlamını sağlar.
Her session başında oku, sonra gerekli dosyaları kendin aç.

---

## MİMARİ

Hexagonal (Ports & Adapters) mimari. Domain katmanı hiçbir dış bağımlılık bilmez.
Bağımlılık yönü: Adapter → Application → Domain. Tersi yasak.

```
src/
├── domain/
│   ├── models/article.py          # Article dataclass — merkezi model
│   ├── ports/
│   │   ├── analysis_port.py       # class AnalysisPort (ABC)
│   │   ├── news_scraper_port.py   # class NewsScraperPort (ABC)
│   │   ├── news_repository_port.py
│   │   ├── messaging_port.py      # class MessagePublisherPort (ABC)
│   │   └── embedding_port.py      # class EmbeddingPort (ABC)
│   └── schemas/
│       └── news_schema.py         # Pydantic: NewsResponse, SearchRequest, SearchResult
├── application/
│   └── services/news_service.py   # Orchestration — port'ları bağlar, reindex_all dahil
├── adapters/
│   ├── analysis/
│   │   └── groq_analyzer.py       # Groq llama-3.1-8b-instant
│   ├── scrapers/
│   │   ├── rss_scrapers.py        # 11 TR+EN RSS kaynağı (BaseRssScraper tabanlı)
│   │   └── registry.py            # SCRAPER_REGISTRY — tek kaynak doğruluk noktası
│   ├── repositories/
│   │   ├── news_orm.py            # SQLAlchemy ORM modeli
│   │   └── news_repository.py     # PostgreSQL adapter
│   ├── messaging/
│   │   ├── kafka_consumer.py      # Worker: consume → scrape → analyze → save → index
│   │   └── kafka_publisher.py
│   ├── scheduling/
│   │   └── scheduler_service.py   # 10dk'da bir Kafka'ya mesaj atar
│   ├── search/
│   │   ├── sentence_transformer_embedder.py  # SentenceTransformerEmbedder (singleton)
│   │   └── chroma_search_repository.py       # ChromaDB adapter — index + search
│   └── api/
│       ├── auth.py               # verify_api_key() dependency (v1.3+)
│       ├── limiter.py            # slowapi Limiter singleton (v1.3+)
│       └── routers/
│           ├── news_router.py    # GET /news, POST /scrape, /search, /reindex, /sources
│           └── health_router.py  # GET /health — DB + Kafka + ChromaDB durumu
├── infrastructure/
│   ├── config/
│   │   ├── database.py           # SQLAlchemy engine — settings üzerinden bağlantı
│   │   └── settings.py           # Pydantic Settings — tek merkezi config (v1.3+)
│   └── logging/
│       └── logger.py             # setup_logging(), JSON/text formatter (v1.3+)
├── dependencies.py                # FastAPI DI — GroqAnalyzer, NewsRepository, ChromaSearch inject
└── main.py                        # FastAPI app
dashboard/
└── app.py                         # Streamlit — API_BASE=http://app:8000, semantik arama dahil
tests/
├── domain/test_article.py
├── application/test_news_service.py
├── adapters/test_rss_scrapers.py
├── adapters/test_news_repository.py
├── adapters/test_groq_analyzer.py
└── adapters/test_chroma_search_repository.py
```

---

## DOCKER SERVİSLER (docker-compose.yml)

| Servis | Port | Açıklama |
|--------|------|----------|
| app | 8000 | FastAPI |
| db | 5432 (env) | PostgreSQL 15 |
| adminer | 8080 | DB yönetim UI |
| zookeeper | 2181 | Kafka koordinatör |
| kafka | 9092 | Mesaj kuyruğu |
| worker | — | Kafka consumer + Groq analyzer |
| scheduler | — | 10dk'da bir scrape tetikler |
| dashboard | 8501 | Streamlit |
| chromadb | 8001 (host) / 8000 (container) | Vektör DB |

Container içi Chroma bağlantısı: `http://chromadb:8000`
Env var: `CHROMA_HOST=chromadb`, `CHROMA_PORT=8000`

---

## KRİTİK KARARLAR VE GEREKÇELERİ

**Neden Groq?** Gemini'den taşındı. 14.400 req/gün ücretsiz, llama-3.1-8b-instant TR+EN destekler, requests kütüphanesi yeterli (SDK yok). Model: `llama-3.1-8b-instant` (70B'den düşürüldü — sentiment extraction için 8B yeterli, TPM limiti 3× daha yüksek). Rate limit: `Retry-After` header kullanılıyor.

**Neden sentence-transformers?** Groq'un embedding API'si yok. `paraphrase-multilingual-MiniLM-L12-v2` modeli TR+EN destekler, tamamen local çalışır, API key gerektirmez. Kurulu versiyon: 3.3.1, torch: 2.10.0, chromadb: 1.5.5

**Neden ChromaDB?** Local, ücretsiz, Docker'a kolay eklenir, persistent storage destekler. `IS_PERSISTENT=TRUE` env var ile volume'a yazar.

**Neden hexagonal?** Kurs projesi — kurumsal mimari dersi için. Separation of concerns önemli. Yeni adapter eklemek domain'i bozmaz.

**Database URL:** `DATABASE_URL` env var yok. Ayrı `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD`, `DB_NAME` kullanılır. `src/infrastructure/config/database.py`'a bak.

**TextBlob:** Tamamen kaldırıldı. Groq ile değiştirildi. Hiçbir yerde TextBlob kullanma.

---

## MEVCUT DURUM

- **Versiyon:** v1.4.0 tamamlandı — v1.5-dev sıradaki
- **Test sayısı:** 145 test, hepsi yeşil
- **CI/CD:** GitHub Actions — push/PR on main, postgres:15 service, `python -m pytest`
- **Branch:** main (tüm özellikler merge edildi)

---

## TAMAMLANAN ÖZELLİKLER (v1.2.0)

### Hybrid Search
- `POST /news/search`: ChromaDB (semantic) + PostgreSQL (keyword) birleşik
- Coverage-based skor, normalize embedding, `1/(1+distance)` formülü

### Haber Kaynakları (11 kaynak)
- TR: TRT Haber, BBC Türkçe, Hürriyet, Hürriyet Spor, Sabah, CNN Türk, Sözcü, Habertürk, HT Spor
- EN: BBC Technology, BBC Sport
- Registry pattern: `src/adapters/scrapers/registry.py` — tek kaynak doğruluk noktası

### Dashboard
- Arama geçmişi (son 8 sorgu, chip olarak gösterilir)
- Detay modalı (`st.dialog`): tam içerik + URL butonu, her kartta `›` butonu
- Stacked bar chart: kaynak bazlı Pozitif/Nötr/Negatif dağılımı
- TR/EN dil desteği (LANGS dict, `L["key"]` sistemi)
- Health göstergesi: status bar'da DB/Kafka/ChromaDB dot'ları + vektör sayısı

### Gözlemlenebilirlik
- `GET /health`: DB + Kafka + ChromaDB durumu + indexed_articles sayısı
- Dashboard status bar'da gerçek zamanlı health dot'ları

### Groq / Model
- Model: `llama-3.1-8b-instant` (70B → 8B, TPM 3× daha yüksek)
- Rate limit: `Retry-After` header kullanılıyor (sabit 10/20/30s yerine)
- Max retry: 3 → 5

---

## BİLİNEN AÇIKLAR (audit sonuçları — v1.3'te giderilecek)

### Kod Kalitesi
- **24× print()** — sadece 2 dosya proper logging kullanıyor (news_service.py, chroma_search_repository.py)
- **5 dosyada dağınık os.getenv()** — merkezi config yok: database.py, scheduler_service.py, groq_analyzer.py, chroma_search_repository.py, health_router.py
- **N+1 query**: `news_repository.py` `article_exists()` her makale için ayrı SELECT çağırıyor
- **Sequential scraping**: `rss_scrapers.py` requests.get() blocking — 11 kaynak için ~8-15sn

### Güvenlik
- **Exposed ports**: PostgreSQL (5433), Kafka (9092), Zookeeper (2181), ChromaDB (8001) host'a açık — internal-only olmalı
- **Sıfır auth**: `/scrape`, `/reindex` endpoint'leri korumasız — herhangi biri tetikleyebilir
- **DoS riski**: `SearchRequest.query` için uzunluk sınırı yok
- **Rate limit yok**: slowapi/throttling eklenmedi
- **CORS konfigürasyonu yok**

---

## SIRADAKİ GÖREVLER (v1.3 → v1.6 Yol Haritası)

Detaylı plan: `C:\Users\eren8\.claude\plans\encapsulated-squishing-willow.md`

Sonraki oturumu başlatmak için: **"v1.5 implementasyonuna başlayalım — plan dosyasını oku, CLAUDE.md'deki yol haritasını takip et."**

### v1.3.0 — Foundation Hardening ✅ TAMAMLANDI
1. **Pydantic Settings** — `src/infrastructure/config/settings.py` oluşturuldu, 5 dosyadaki os.getenv() kaldırıldı
2. **Structured Logging** — `src/infrastructure/logging/logger.py` (JSON/text formatter), 24 print() → logger
3. **Network isolation** — docker-compose.yml: db/kafka/zookeeper/chromadb port'ları kapatıldı
4. **API Key Auth** — `src/adapters/api/auth.py`, `/scrape` ve `/reindex` → `Depends(verify_api_key)`
5. **Rate limiting** — slowapi: search 30/dk, scrape 6/dk, news list 120/dk; `src/adapters/api/limiter.py`
6. **Input validation** — SearchRequest.query max_length=200, ScrapeCommand validasyonu, sentiment pattern
7. **CORS** — CORSMiddleware, `settings.cors_origins` üzerinden yapılandırılabilir

Sonuç: 97 → 131 test (+34)

### v1.4.0 — Performance & UX ✅ TAMAMLANDI
1. **Async scraping** — httpx.AsyncClient + follow_redirects, `_fetch_content()` testability
2. **Batch processing** — `bulk_exists()` tek SQL sorgusu, N+1 elimine, Groq quota tasarrufu
3. **PostgreSQL indexes** — source, sentiment_label, created_at
4. **pub_date capture** — RSS `<pubDate>`/`<published>` → Article.published_at → dashboard
5. **Docker image split** — `Dockerfile.light` scheduler+dashboard (~600MB vs ~9.5GB)
6. **App healthcheck** — SentenceTransformer startup preload, dashboard service_healthy bekliyor
7. **Redis cache** — v1.5'e ertelendi (opsiyonel)

Sonuç: 131 → 145 test (+14)

### v1.5.0 — AI Features (~3-5 gün)
1. **NER** — Groq prompt'a entities + topic ekle, Article model genişlet
2. **Topic filter** — dashboard'da Technology/Sports/Economy/Politics pills
3. **Trending engine** — `GET /news/trending?hours=6` — entity aggregate
4. **Semantic dedup** — ChromaDB 0.92+ similarity → duplicate flag

Beklenen: ~122 → ~130 test

### v1.6.0 — Production Deployment (~5-7 gün)
1. **Nginx + HTTPS** — reverse proxy, Let's Encrypt, sadece 80/443 açık
2. **Prometheus + Grafana + Loki** — metrics, dashboard, log aggregation
3. **Backup otomasyonu** — pg_dump + ChromaDB volume, günde 1×
4. **docker-compose.prod.yml** — resource limits, healthcheck'ler, restart policy

Beklenen: ~130 → ~135 test

### Beyond v1.6 — Kasıtlı Kapsam Dışı
JWT auth, WebSocket, NTV Playwright scraper, K8s/Helm, Qdrant migration, CQRS, Next.js rewrite — bu ölçek için fayda/maliyet uygun değil.

---

## KODLAMA KURALLARI

- Port isimleri: `*Port` (AnalysisPort, EmbeddingPort)
- Adapter isimleri: açıklayıcı (`GroqAnalyzer`, `SentenceTransformerEmbedder`)
- Import sırası: stdlib → third party → local (src.*)
- **v1.2 ve öncesi:** env var'lar `os.getenv()` ile okunuyor — `src/infrastructure/config/database.py`'a bak
- **v1.3'ten itibaren:** `from src.infrastructure.config.settings import settings` kullan (Pydantic Settings)
- Exception'ları yut, logla, fallback dön — servis çökmemeli
- Test'lerde gerçek API çağrısı yok, her şey mock

---

## ÇALIŞMA KOMUTLARI

```powershell
# Test
venv\Scripts\python.exe -m pytest tests/ -v

# Belirli test dosyası
venv\Scripts\python.exe -m pytest tests/adapters/test_groq_analyzer.py -v

# Docker — kod değiştiyse
docker-compose restart worker
docker-compose restart app

# Docker — requirements değiştiyse
docker-compose up --build

# Docker — sıfırdan (DB + ChromaDB silinir)
docker-compose down -v && docker-compose up --build

# Loglar
docker logs nexstream_worker --tail 30
docker logs nexstream_chromadb --tail 20
```

---

## BİLİNEN NOTLAR

- Groq free tier: 14.400 req/gün — production'da dikkat
- Scraper limit: 25 haber/kaynak/çalışma
- DB duplicate kontrolü var — aynı URL tekrar kaydedilmez
- NTV scrapers çalışmıyor (HTML dönüyor, RSS yok) — ekleme
- ChromaDB 1.5.5 kurulu (0.5.23 uvicorn conflict veriyordu)
- `docker-compose down -v` sonrası ChromaDB da sıfırlanır
- Dashboard sidebar kaldırıldı, tüm kontroller üst bar'da
- README UTF-8 BOM'suz olarak yeniden yazıldı (önceki versiyon UTF-16 idi, GitHub'da bozuk görünüyordu)
