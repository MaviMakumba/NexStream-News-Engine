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
│       └── news_schema.py         # Pydantic: NewsResponse, SearchRequest, SearchResult, TrendingResponse
├── application/
│   └── services/news_service.py   # Orchestration — port'ları bağlar, reindex_all, get_trending dahil
├── adapters/
│   ├── analysis/
│   │   └── groq_analyzer.py       # Groq llama-3.1-8b-instant — sentiment + NER + topic (v1.5+)
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
│   │   └── chroma_search_repository.py       # ChromaDB adapter — index + search + dedup (v1.5+)
│   └── api/
│       ├── auth.py               # verify_api_key() dependency (v1.3+)
│       ├── limiter.py            # slowapi Limiter singleton (v1.3+)
│       ├── metrics.py            # Prometheus custom metrics (v1.6+)
│       └── routers/
│           ├── news_router.py    # GET /news, /trending, POST /scrape, /search, /reindex, /sources
│           └── health_router.py  # GET /health — DB + Kafka + ChromaDB durumu
├── infrastructure/
│   ├── config/
│   │   ├── database.py           # SQLAlchemy engine — settings üzerinden bağlantı
│   │   └── settings.py           # Pydantic Settings — tek merkezi config (v1.3+)
│   └── logging/
│       └── logger.py             # setup_logging(), JSON/text formatter (v1.3+)
├── dependencies.py                # FastAPI DI — GroqAnalyzer, NewsRepository, ChromaSearch inject
└── main.py                        # FastAPI app
migrations/
└── v1_5_add_entities_topic.sql    # v1.5 DB migration (entities, topic, is_duplicate)
dashboard/
└── app.py                         # Streamlit — 5 tema, TR/EN, trend/topic/dedup UI (v1.5+)
tests/
├── domain/test_article.py
├── application/test_news_service.py
├── adapters/test_rss_scrapers.py
├── adapters/test_news_repository.py
├── adapters/test_groq_analyzer.py
├── adapters/test_chroma_search_repository.py
├── adapters/test_ner_prompt.py            # NER + topic Groq çıktısı (v1.5+)
├── adapters/test_semantic_dedup.py        # is_near_duplicate testleri (v1.5+)
├── adapters/test_trending_endpoint.py     # Trending engine testleri (v1.5+)
└── adapters/test_prometheus_metrics.py    # /metrics endpoint + custom counters (v1.6+)
infra/
├── nginx/
│   ├── nginx.conf                         # Production: SSL, gzip, security headers, certbot
│   └── nginx.dev.conf                     # Dev: HTTP-only, same routing
├── prometheus/
│   └── prometheus.yml                     # Scrape config: nexstream-api job
├── grafana/
│   ├── provisioning/
│   │   ├── datasources/datasources.yml   # Prometheus + Loki auto-provisioned
│   │   └── dashboards/dashboards.yml     # File-based dashboard provider
│   └── dashboards/nexstream.json         # Pre-built panels: latency, articles, Groq, search
├── loki/
│   ├── loki-config.yml                   # TSDB schema, filesystem storage
│   └── promtail-config.yml              # Docker SD, container labels
└── backup/
    ├── Dockerfile                         # Alpine + pg_dump + crond
    ├── backup.sh                          # pg_dump + ChromaDB tar + retention cleanup
    └── crontab                            # Daily 03:00 UTC
docker-compose.prod.yml                    # Full production stack (16 services)
```

---

## DOCKER SERVİSLER

### docker-compose.yml (geliştirme)

| Servis | Port | Açıklama |
|--------|------|----------|
| app | 8000 | FastAPI |
| db | — (internal) | PostgreSQL 15 |
| adminer | 8080 | DB yönetim UI |
| zookeeper | — (internal) | Kafka koordinatör |
| kafka | — (internal) | Mesaj kuyruğu |
| worker | — | Kafka consumer + Groq analyzer |
| scheduler | — | 10dk'da bir scrape tetikler |
| dashboard | 8501 | Streamlit |
| chromadb | — (internal) | Vektör DB |

### docker-compose.prod.yml (production)

| Servis | Port | Açıklama |
|--------|------|----------|
| nginx | 80, 443 | Reverse proxy + TLS termination |
| certbot | — | Let's Encrypt otomatik yenileme |
| app | — (internal) | FastAPI + /metrics endpoint |
| db | — (internal) | PostgreSQL 15 |
| zookeeper | — (internal) | Kafka koordinatör |
| kafka | — (internal) | Mesaj kuyruğu |
| worker | — (internal) | Kafka consumer + Groq analyzer |
| scheduler | — (internal) | 10dk'da bir scrape tetikler |
| dashboard | — (internal) | Streamlit (nginx üzerinden) |
| chromadb | — (internal) | Vektör DB |
| prometheus | — (monitoring) | Metric scraping, 30 gün retention |
| grafana | — (via nginx) | Dashboard + alerting |
| loki | — (monitoring) | Log aggregation |
| promtail | — (monitoring) | Docker log collector |
| backup | — (internal) | Günlük pg_dump + ChromaDB tar |

Container içi Chroma bağlantısı: `http://chromadb:8000`
Env var: `CHROMA_HOST=chromadb`, `CHROMA_PORT=8000`

---

## KRİTİK KARARLAR VE GEREKÇELERİ

**Neden Groq?** Gemini'den taşındı. 14.400 req/gün ücretsiz, llama-3.1-8b-instant TR+EN destekler, requests kütüphanesi yeterli (SDK yok). Model: `llama-3.1-8b-instant` (70B'den düşürüldü — sentiment + NER + topic extraction için 8B yeterli, TPM limiti 3× daha yüksek). Rate limit: `Retry-After` header kullanılıyor. v1.5'ten itibaren tek prompt'ta sentiment + entities + topic çıkarılıyor (max_tokens=350).

**Neden sentence-transformers?** Groq'un embedding API'si yok. `paraphrase-multilingual-MiniLM-L12-v2` modeli TR+EN destekler, tamamen local çalışır, API key gerektirmez. Kurulu versiyon: 3.3.1, torch: 2.10.0, chromadb: 1.5.5

**Neden ChromaDB?** Local, ücretsiz, Docker'a kolay eklenir, persistent storage destekler. `IS_PERSISTENT=TRUE` env var ile volume'a yazar.

**Neden hexagonal?** Kurs projesi — kurumsal mimari dersi için. Separation of concerns önemli. Yeni adapter eklemek domain'i bozmaz.

**Database URL:** `DATABASE_URL` env var yok. Ayrı `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD`, `DB_NAME` kullanılır. `src/infrastructure/config/database.py`'a bak.

**TextBlob:** Tamamen kaldırıldı. Groq ile değiştirildi. Hiçbir yerde TextBlob kullanma.

---

## MEVCUT DURUM

- **Versiyon:** v1.7.0 ✅ TAMAMLANDI — WebSocket, API v1, RSS feed, Email Newsletter & Keyword Alert hepsi bitti
- **Test sayısı:** 217 test, hepsi yeşil
- **CI/CD:** GitHub Actions — push/PR on main, postgres:15 service, `python -m pytest`
- **Branch:** main (tüm özellikler merge edildi)
- **Hedef:** CV/portfolio projesi → canlı ürüne geçiş (ücretsiz başla, gelir varsa harca)
- **Kısıt:** VPS'te 7/24 bağımsız çalışacak, local bağımlılık yok

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

## TAMAMLANAN MİLESTONE'LAR (v1.3 → v1.6)

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

### v1.5.0 — AI Features ✅ TAMAMLANDI
1. **NER** — Groq prompt'a entities (persons/organizations/locations) + topic eklendi, Article model genişletildi
2. **Topic filter** — dashboard'da Technology/Sports/Economy/Politics/Health/Culture/World/Other pills
3. **Trending engine** — `GET /news/trending?hours=6&limit=10` — entity aggregate, tıklanabilir trend pills
4. **Semantic dedup** — ChromaDB `is_near_duplicate()` 0.92 threshold → `is_duplicate` flag
5. **Summary surface** — Detay modalında önce summary, tam içerik expander'da; entity chips
6. **DB migration** — `migrations/v1_5_add_entities_topic.sql` (entities JSON, topic, is_duplicate)
7. **Dashboard UX overhaul** — Admin butonları kaldırıldı (pipeline tamamen otomatik), 5 tema (3 karanlık + 2 aydınlık: Snow/Sand), Türkiye saati, tüm etiketler TR/EN lokalize, sentiment scoring iyileştirildi (tam aralık kullanımı), arama sonuçları tam ekran, haber sayısı/yenileme segmented control
8. **Auto reanalyze** — Worker her çevrimi sonunda entities=NULL olan haberleri otomatik analiz eder
9. **Groq prompt** — Sentiment score aralıkları netleştirildi, summary haberin dilinde üretiliyor
10. **`POST /news/reanalyze`** — Eski haberleri yeni prompt ile toplu analiz endpoint'i

Sonuç: 145 → 173 test (+28)

### v1.6.0 — Production Deployment ✅ TAMAMLANDI
1. **Nginx + HTTPS** — `infra/nginx/nginx.conf` reverse proxy (app + dashboard + grafana), gzip, security headers, Let's Encrypt certbot, sadece 80/443 açık
2. **Prometheus + Grafana + Loki** — `infra/prometheus/`, `infra/grafana/`, `infra/loki/` tam observability stack; `prometheus-fastapi-instrumentator` ile `/metrics` endpoint; custom metrics: `nexstream_articles_processed_total`, `nexstream_groq_latency_seconds`, `nexstream_groq_rate_limit_total`, `nexstream_search_latency_seconds`
3. **Backup otomasyonu** — `infra/backup/backup.sh` pg_dump + ChromaDB volume tar, günde 1× cron, 7 gün retention
4. **docker-compose.prod.yml** — resource limits, healthcheck'ler, restart policy `always`, network isolation (backend internal, monitoring internal, frontend exposed), pre-provisioned Grafana datasources + dashboard

Sonuç: 173 → 180 test (+7)

### v1.7.0 — Kullanıcı Etkileşimi & API Ürünü ✅ TAMAMLANDI
1. **WebSocket canlı akış** — `/ws/feed` endpoint, `WebSocketNotifier` adapter, dashboard canlı ticker, DB polling broadcast task
2. **Email Newsletter & Keyword Alert** — `ConsoleEmailAdapter` + `ResendEmailAdapter` (Resend API), günlük digest (top 10 haber, `newsletter_job.py`), instant keyword alert (`_send_keyword_alerts`), `Subscriber` domain model + `SubscriberRepositoryPort` + PostgreSQL adapter
3. **Public API v1** — `/api/v1/news`, cursor-based pagination, `X-RateLimit-*` header'ları
4. **RSS/Atom feed** — `/feed.xml`, `feedgen` kütüphanesi, sentiment + topic tag'leri
5. **Kullanıcı abonelik API'si** — `POST/DELETE/PATCH/GET /subscriptions/`, email-validator, frekans (daily/instant/never), keyword/kaynak/konu tercihleri
6. **Türkçe arama iyileştirmesi** — morfolojik suffix stripping (`_TR_SUFFIXES`), `_stem_tr()`, `_tokenize()` token genişletme
7. **Tema güncellemesi** — Snow/Sand kaldırıldı, Dusk (Catppuccin) + Ocean (navy-teal) eklendi
8. **Teknik iyileştirmeler** — Kafka singleton (`startup_done` flag), health router singleton, JSON logging (print → logger), README UTF-8 düzeltmesi

Sonuç: 180 → 217 test (+37)

---

## SIRADAKİ GÖREVLER (v1.7 → v2.0 Yol Haritası)

Detaylı plan: `C:\Users\eren8\.claude\plans\ancient-watching-crescent.md`

Sonraki oturumu başlatmak için: **"v1.8 implementasyonuna başlayalım — CLAUDE.md'deki yol haritasını takip et."**

### v1.7.0 — Kullanıcı Etkileşimi & API Ürünü ✅ TAMAMLANDI
Sonuç: 180 → 217 test (+37). Detaylar yukarıdaki tamamlanan milestone'larda.

### v1.8.0 — AI & Veri Kalitesi (~14-18 gün)
1. **Kaynak genişletme** — Reuters, Guardian Tech, TechCrunch, Hacker News, Anadolu Ajansı, Ekonomist (5-8 yeni RSS)
2. **Haber ilişki grafı** — `GET /news/{id}/related`, entity overlap ile ilgili haberler, dashboard'da "İlgili haberler"
3. **Kaynak güvenilirlik skorlaması** — çapraz doğrulama, `credibility_score` + `corroboration_count`
4. **Cloud LLM fallback** — Groq birincil, HuggingFace Inference API yedek (VPS'te çalışır, local değil), `FallbackAnalyzer`
5. **İçerik kalite skorlama** — uzunluk, entity yoğunluğu, faktüel dil göstergeleri

Beklenen: ~215 → ~255 test (+40)

### v1.9.0 — Monetizasyon Temeli (~16-20 gün)
1. **Hafif kullanıcı hesapları** — email + bcrypt, session token (JWT yok), profil
2. **Katmanlı API erişimi** — Free (100 req/gün) / Pro ($9.99/ay, 2000 req/gün, WebSocket) / Enterprise ($49.99/ay, sınırsız)
3. **Kullanım takibi & analytics** — user bazlı API log, admin endpoint, Grafana panel
4. **Stripe ödeme** — Checkout + webhook + hosted billing portal
5. **Redis cache katmanı** — trending (5dk), news list (1dk), session'lar
6. **Newsletter sponsorluk alanı** — digest'te sponsor bölümü, admin panel

Beklenen: ~255 → ~300 test (+45)

### v2.0.0 — Public Launch (~10-14 gün)
1. **Domain & VPS** — `nexstream.news`, Hetzner CX22 (€4.51/ay), Cloudflare CDN, UptimeRobot
2. **Landing page** — Static HTML + Tailwind, Hero/Features/Pricing/Sign Up, TR/EN
3. **API dökümantasyon portalı** — Swagger/Redoc, kullanım örnekleri, demo API key, Postman collection
4. **SEO & içerik** — blog yazıları, OpenGraph, JSON-LD, sitemap.xml, Product Hunt launch
5. **GitHub README overhaul** — Mermaid mimari diyagramı, dashboard GIF demo, badge'ler

Beklenen: ~300 → ~320 test (+20)

### Kasıtlı Kapsam Dışı (fayda/maliyet uygun değil)
K8s/Helm, Qdrant migration, CQRS, Next.js rewrite, NTV Playwright scraper, Twitter/X entegrasyonu, custom billing portal

---

## PRODUCTION DEPLOYMENT NOTLARI (v1.6+)

### İlk deployment adımları
1. VPS'e (DigitalOcean/Hetzner/Oracle Free) Docker + Docker Compose kurulur
2. `.env` dosyası production değerlerle oluşturulur (`API_KEY`, `GRAFANA_PASSWORD` güçlü değerler)
3. SSL sertifikası: `infra/nginx/ssl/` dizinine self-signed cert koy, sonra certbot ile değiştir
4. `docker-compose -f docker-compose.prod.yml up -d`
5. Certbot ilk çalıştırma: `docker-compose -f docker-compose.prod.yml exec certbot certbot certonly --webroot -w /var/www/certbot -d your-domain.com`

### Gözlemlenebilirlik
- Grafana: `https://your-domain/grafana/` (admin/nexstream varsayılan)
- Pre-provisioned datasources: Prometheus + Loki
- NexStream dashboard: request latency, articles/min, Groq latency/rate limits, search latency
- Worker logları: Grafana → Explore → Loki → `{service="worker"}`

### Backup
- Günlük 03:00 UTC: PostgreSQL pg_dump + ChromaDB tar
- `/backups` volume'unda 7 gün retention
- Manuel tetikleme: `docker exec nexstream_backup /usr/local/bin/backup.sh`

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

# Docker — kod değiştiyse (volume mount sayesinde build GEREKMEZ)
docker-compose restart worker
docker-compose restart app
docker-compose restart dashboard

# Docker — ilk çalıştırma veya requirements/Dockerfile değiştiyse (SADECE bu durumda build)
docker-compose up --build -d

# Docker — sıfırdan (DB + ChromaDB silinir)
docker-compose down -v && docker-compose up --build -d

# Docker — gereksiz image/cache temizliği
docker builder prune -f && docker volume prune -f

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
- `prometheus-fastapi-instrumentator` app'e eklendi, `/metrics` endpoint Prometheus format döndürür
- `docker-compose.prod.yml` production için, `docker-compose.yml` dev için kullanılır
- `infra/nginx/nginx.dev.conf` SSL olmadan local test için (nginx.conf SSL gerektirir)
- Worker sıralı işleme: `asyncio.create_task` → `await` + 2sn throttle, Groq rate limit patlamasını önler
