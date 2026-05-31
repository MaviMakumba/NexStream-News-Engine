<div align="center">

# NexStream News Engine

**AI-Powered Multi-Source News Intelligence Platform**

[![Tests](https://github.com/MaviMakumba/NexStream-News-Engine/actions/workflows/tests.yml/badge.svg)](https://github.com/MaviMakumba/NexStream-News-Engine/actions/workflows/tests.yml)
![Python](https://img.shields.io/badge/Python-3.11-blue?logo=python)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?logo=fastapi)
![Next.js](https://img.shields.io/badge/Next.js-14-000000?logo=nextdotjs)
![Kafka](https://img.shields.io/badge/Apache_Kafka-231F20?logo=apachekafka)
![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker)
![Tests](https://img.shields.io/badge/tests-343_passing-brightgreen)
![License](https://img.shields.io/badge/License-MIT-green)

[English](#english) · [Türkçe](#turkce)

</div>

---

<a name="english"></a>
## English

### Overview

NexStream is an event-driven news aggregation and intelligence platform. It continuously collects articles from **17 sources** in Turkish and English, runs them through an AI pipeline (sentiment, named-entity recognition, topic classification, summarization, plus quality and source-credibility scoring), enables hybrid semantic + keyword search, and surfaces everything through a **Next.js frontend with a cinematic, multi-theme UI**.

What started as a course project on enterprise architecture has grown into a production-shaped SaaS: user accounts, a tiered public API with usage metering, Stripe billing, a real-time WebSocket feed, email newsletters, and a full observability stack.

**Key capabilities:**
- **17 sources** (11 Turkish + 6 English), added declaratively via a scraper registry
- **AI pipeline** on Groq `llama-3.1-8b-instant`: sentiment + entities (people/orgs/locations) + topic + summary in a single prompt, with an optional Hugging Face fallback
- **Hybrid search**: ChromaDB semantic vectors + PostgreSQL keyword, combined-score ranked, with Turkish morphological stemming
- **Trending engine**, **related-article graph** (entity overlap), and **semantic dedup**
- **Quality + credibility scoring**: deterministic content-quality score and source-credibility / corroboration metrics
- **Real-time WebSocket feed**, **email newsletter + instant keyword alerts**, **RSS/Atom feed**
- **User accounts** (session auth), **tiered API** (Free / Pro / Enterprise) with per-user rate limits and usage analytics, **Stripe billing**, **Redis cache**
- **Next.js frontend**: 9 cinematic themes with animated Canvas backgrounds, full TR/EN i18n
- **Event-driven** via Apache Kafka; **fully containerized** with Docker Compose
- **Observability**: Prometheus + Grafana + Loki, `/health` and `/metrics` endpoints
- **343 tests**, all green, CI via GitHub Actions

---

### Architecture

NexStream is built on **Hexagonal Architecture (Ports & Adapters)**. The domain layer has zero knowledge of external systems; adapters implement ports and are wired together in `dependencies.py`. Dependency direction is strictly **Adapter → Application → Domain**.

```
+--------------------------------------------------------------+
|                        DOMAIN LAYER                          |
|   Article model · Ports (ABCs) · Schemas · Scoring (pure)    |
+--------------------------------------------------------------+
                              |
+--------------------------------------------------------------+
|                     APPLICATION LAYER                        |
|        NewsService — orchestration, metadata enrichment      |
+--------------------------------------------------------------+
                              |
+--------------------------------------------------------------+
|                       ADAPTERS LAYER                         |
|                                                              |
|  Scrapers        Analyzer            Repository      API     |
|  --------        --------            ----------      ---     |
|  17 RSS feeds    Groq + HF fallback  PostgreSQL      FastAPI |
|  (registry)      (sentiment/NER/     SQLAlchemy      REST +  |
|                   topic/summary)                     v1 API  |
|                                                              |
|  Messaging       Scheduling          Vector Search   Auth    |
|  ---------       ----------          -------------   ----    |
|  Apache Kafka    APScheduler         ChromaDB +      Session |
|  (producer +     (10-min trigger)    sentence-       + Redis |
|   consumer)                          transformers    + tiers |
+--------------------------------------------------------------+
```

**Event flow:**

```
Scheduler (every 10 min)
        |
        v
Kafka topic: news_updates  ──>  Kafka worker (consumer)
                                        |
                    fetch ──> RSS scraper (17 sources)
                    analyze ─> Groq analyzer (sentiment/NER/topic/summary)
                    score ──> quality + credibility + corroboration
                    persist ─> PostgreSQL
                    index ──> ChromaDB (embeddings, dedup)
                    notify ─> WebSocket broadcast + keyword alerts
                                        |
                                        v
                        Next.js frontend  ·  Public API v1  ·  RSS feed
```

---

### Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Next.js 14 + React + TypeScript — 9 cinematic themes (pure CSS + Canvas) |
| API | FastAPI + Uvicorn (REST + versioned `/api/v1`) |
| Auth & limits | Session tokens (bcrypt), slowapi rate limiting, per-tier quotas |
| Message broker | Apache Kafka + Zookeeper |
| AI analyzer | Groq `llama-3.1-8b-instant` (+ optional Hugging Face fallback) |
| Embeddings | `paraphrase-multilingual-MiniLM-L12-v2` (local, no API key) |
| Vector search | ChromaDB (persistent) |
| Database | PostgreSQL 15 + SQLAlchemy ORM |
| Cache | Redis 7 (sessions / trending; null-cache fallback) |
| Payments | Stripe (Checkout + webhook + billing portal) |
| Email | Resend API (newsletter + keyword alerts), console adapter for dev |
| Scheduler | APScheduler |
| Observability | Prometheus + Grafana + Loki + Promtail |
| Reverse proxy | Nginx + Let's Encrypt (production) |
| Containerization | Docker + Docker Compose |
| CI/CD | GitHub Actions |
| Testing | pytest (343 tests) |

---

### News Sources (17)

| Source | Language | Category |
|--------|----------|----------|
| TRT Haber | Turkish | General |
| BBC Türkçe | Turkish | General |
| Hürriyet | Turkish | General |
| Hürriyet Spor | Turkish | Sports |
| Sabah | Turkish | General |
| CNN Türk | Turkish | General |
| Sözcü | Turkish | General |
| Habertürk | Turkish | General |
| HT Spor | Turkish | Sports |
| Anadolu Ajansı | Turkish | General |
| AA Ekonomi | Turkish | Economy |
| BBC Technology | English | Technology |
| BBC Sport | English | Sports |
| Guardian Tech | English | Technology |
| TechCrunch | English | Technology |
| Hacker News | English | Technology |
| The Verge | English | Technology |

New sources can be added in a few lines — see [Adding a News Source](#adding-a-news-source).

---

### Frontend (Next.js)

The original Streamlit dashboard was replaced by a **Next.js 14 + React** frontend with a distinctive **cinematic theme system**:

- **9 cinematic themes** — Matrix, Godfather, Blade Runner, Dune, Star Wars, Spider-Man, Batman, Wolfenstein + a clean **Day** mode. Each theme transforms colors, fonts, an animated full-screen **Canvas background** (digital rain, film grain, neon rain, sandstorm, starfield, web mesh, bat-signal, embers) and plays a transition flash on switch. **Pure CSS + Canvas — no images or video assets.**
- **Theme registry** (`lib/theme/registry.ts`): single source of truth. Adding a theme = one registry entry + one CSS block + one Canvas effect, with zero consumer changes (Open/Closed). All effects share one `requestAnimationFrame` loop (`useCanvasScene`).
- **Full TR / EN i18n**: every string lives in `lib/i18n.ts` — landing, dashboard, account, and admin pages all switch language together.
- **Pages**: landing (hero / features / pricing), auth (login / register), dashboard (filters + trending pills + infinite list), semantic search, account (plan + billing), admin (usage + sponsors).
- Honors `prefers-reduced-motion` and pauses animations when the browser tab is hidden.

---

### API Endpoints (selected)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/news` | List articles — cursor pagination, `X-RateLimit-*` headers, tier-gated |
| POST | `/api/v1/news/search` | Hybrid semantic + keyword search |
| GET | `/api/v1/news/trending` | Trending entities (last N hours) |
| GET | `/api/v1/news/{id}/related` | Related articles via entity overlap |
| GET | `/api/v1/news/sources` | Registered sources |
| POST | `/auth/register` · `/auth/login` · `/auth/logout` | Session-based auth |
| GET/POST/PATCH/DELETE | `/subscriptions` | Newsletter / keyword-alert preferences |
| POST | `/billing/checkout` · `/billing/portal` | Stripe Checkout & billing portal |
| GET | `/admin/usage` · `/admin/sponsors` | Admin analytics & sponsor CRUD (`X-API-Key`) |
| GET | `/feed.xml` | RSS/Atom feed |
| WS | `/ws/feed` | Real-time article stream |
| POST | `/news/scrape` · `/news/reindex` · `/news/reanalyze` | Maintenance (`X-API-Key`) |
| GET | `/health` · `/metrics` | Health (DB/Kafka/ChromaDB) · Prometheus metrics |
| GET | `/docs` | Swagger UI |

---

### Getting Started

#### Prerequisites
- Docker Desktop
- Git
- Groq API key (free at [console.groq.com](https://console.groq.com))

#### Installation

```bash
# 1. Clone the repository
git clone https://github.com/MaviMakumba/NexStream-News-Engine.git
cd NexStream-News-Engine

# 2. Create the environment file
cp .env.example .env

# 3. Add your Groq API key to .env
GROQ_API_KEY=gsk_xxxxxxxxxxxxxxxxxxxx

# 4. Start the full stack
docker compose up -d
```

#### Services

| Service | URL | Description |
|---------|-----|-------------|
| Frontend | http://localhost:3000 | Next.js UI |
| API | http://localhost:8000 | FastAPI REST |
| API Docs | http://localhost:8000/docs | Swagger UI |
| DB Admin | http://localhost:8080 | Adminer |

#### First Run

Once all containers are healthy, open the frontend at `http://localhost:3000`. The scheduler triggers scraping every 10 minutes and the Kafka worker processes articles through the AI analyzer automatically — no manual action needed. Confirm `http://localhost:8000/health` shows DB, Kafka, and ChromaDB all green.

> **Clean start/stop:** use `docker compose down` then `docker compose up -d`. Kafka, Zookeeper, and ChromaDB run with `restart: unless-stopped`, so the stack self-heals even after an abrupt shutdown.

#### Frontend development (optional, outside Docker)

```bash
cd frontend
npm install
npm run dev      # http://localhost:3000 (hot reload)
npm run build    # type-check + production build
```

---

### Running Tests

```bash
pip install -r requirements.txt
python -m pytest tests/ -v
```

**Test coverage: 343 tests** across domain, application, and adapter layers. Every external call (Groq, Kafka, DB, ChromaDB) is mocked — no network access required.

---

### Adding a News Source

Thanks to the `BaseRssScraper` pattern and the source registry, adding a source takes only a few lines:

```python
# src/adapters/scrapers/rss_scrapers.py
class MyNewsScraper(BaseRssScraper):
    def __init__(self):
        self.url = "https://example.com/rss"
        self.source_name = "My News"
        self.limit = 25
```

Then register it in `src/adapters/scrapers/registry.py`:

```python
SCRAPER_REGISTRY = {
    ...
    "My News": MyNewsScraper(),
}
```

---

### Adding a New AI Analyzer

Implement the `AnalysisPort` interface and wire it through `adapters/analysis/factory.py` — zero changes to business logic:

```python
# src/adapters/analysis/my_analyzer.py
class MyAnalyzer(AnalysisPort):
    def analyze_text(self, text: str) -> dict:
        return {"sentiment_score": 0.8, "sentiment_label": "Positive", "summary": "..."}
```

The default `FallbackAnalyzer` chains Groq → Hugging Face → neutral fallback so a single provider outage never crashes the worker.

---

### Environment Variables

| Variable | Description | Default / Example |
|----------|-------------|-------------------|
| `GROQ_API_KEY` | Groq API key | `gsk_xxx...` |
| `HUGGINGFACE_API_KEY` | Optional analyzer fallback (disabled if empty) | — |
| `DB_HOST` / `DB_PORT` / `DB_NAME` / `DB_USER` / `DB_PASSWORD` | PostgreSQL connection | `db` / `5432` / `nexstream_db` / … |
| `CHROMA_HOST` / `CHROMA_PORT` | ChromaDB connection | `chromadb` / `8000` |
| `KAFKA_BOOTSTRAP_SERVERS` | Kafka brokers | `kafka:29092` |
| `REDIS_URL` | Redis cache (null-cache if empty) | `redis://redis:6379/0` |
| `API_KEY` | Shared admin/maintenance key | `dev-key-change-me` |
| `SESSION_TTL_DAYS` | Session token lifetime | `30` |
| `CORS_ORIGINS` | Allowed origins | `http://localhost:3000,...` |
| `RESEND_API_KEY` | Email newsletter (console adapter if empty) | — |
| `STRIPE_SECRET_KEY` / `STRIPE_WEBHOOK_SECRET` | Stripe billing (`/billing/*` returns 503 if unset) | — |
| `STRIPE_PRO_PRICE_ID` / `STRIPE_ENTERPRISE_PRICE_ID` | Stripe price IDs | — |

---

### API Tiers

| Tier | Price | Daily API quota | Highlights |
|------|-------|-----------------|------------|
| Free | $0 | 100 requests | News & semantic search, daily digest |
| Pro | $9.99 / mo | 2,000 requests | WebSocket feed, 50 search results, keyword alerts, relation graph |
| Enterprise | $49.99 / mo | Unlimited | Raw data export, custom sources, SLA, priority support |

> Billing requires Stripe configuration; without it the upgrade endpoints intentionally return `503`. Admin endpoints use the shared `API_KEY` (not per-user keys).

---

### CI/CD

Every push / PR to `main` triggers GitHub Actions:

1. Spins up a PostgreSQL 15 service container
2. Installs Python dependencies (incl. `pytest-asyncio`)
3. Runs all 343 tests with `pytest`
4. Reports pass/fail status

---

### Roadmap

| Milestone | Focus | Status |
|-----------|-------|--------|
| v1.2 | Hybrid search, 11 sources, dashboard, health endpoint | ✅ Done |
| v1.3 | Foundation hardening: Pydantic Settings, logging, API auth, rate limiting, CORS | ✅ Done |
| v1.4 | Performance: async scraping, batch processing, DB indexes, `pub_date` | ✅ Done |
| v1.5 | AI: NER, topic classification, trending engine, semantic dedup, reanalyze | ✅ Done |
| v1.6 | Production deploy: Nginx + HTTPS, Prometheus + Grafana + Loki, backups | ✅ Done |
| v1.7 | WebSocket feed, newsletter + keyword alerts, public API v1, RSS feed, subscriptions | ✅ Done |
| v1.8 | Source expansion (17), related graph, quality + credibility scoring, LLM fallback | ✅ Done |
| v1.9 | User accounts, tiered API, usage analytics, Stripe billing, Redis cache, sponsors | ✅ Done |
| v1.10 | Cinematic-theme Next.js frontend (9 themes), full i18n, Kafka resilience | ✅ Done |
| v2.0 | Public launch: domain + VPS, landing SEO, API docs portal, Product Hunt | 🔜 Planned |

---

### License

MIT License — see [LICENSE](LICENSE) for details.

---

<a name="turkce"></a>
## Türkçe

### Genel Bakış

NexStream, **17 kaynaktan** Türkçe ve İngilizce haber toplayan, bunları bir yapay zeka hattından (duygu, varlık tanıma, konu sınıflandırma, özetleme + kalite ve kaynak güvenilirliği skorlaması) geçiren, hibrit anlamsal + anahtar kelime araması sunan ve her şeyi **sinematik, çok temalı bir Next.js arayüzünde** gösteren olay güdümlü bir haber platformudur.

Kurumsal mimari dersi için başlayan proje; kullanıcı hesapları, kullanım ölçümlü katmanlı bir API, Stripe ödeme, gerçek zamanlı WebSocket akışı, e-posta bülteni ve tam bir gözlemlenebilirlik yığını ile production'a yakın bir SaaS'a dönüştü.

**Temel özellikler:**
- **17 kaynak** (11 TR + 6 EN), scraper registry ile bildirimsel eklenir
- **AI hattı** (Groq `llama-3.1-8b-instant`): tek prompt'ta duygu + varlıklar (kişi/kurum/yer) + konu + özet; opsiyonel Hugging Face yedeği
- **Hibrit arama**: ChromaDB anlam vektörü + PostgreSQL anahtar kelime, birleşik skor; Türkçe morfolojik kök ayıklama
- **Trending motoru**, **ilişki grafı** (varlık örtüşmesi) ve **anlamsal dedup**
- **Kalite + güvenilirlik skorlaması**: deterministik içerik kalitesi + kaynak güvenilirliği / doğrulama metrikleri
- **Gerçek zamanlı WebSocket akışı**, **e-posta bülteni + anlık keyword alert**, **RSS/Atom feed**
- **Kullanıcı hesapları** (session auth), **katmanlı API** (Free / Pro / Enterprise) kullanıcı bazlı limit + analytics, **Stripe ödeme**, **Redis cache**
- **Next.js arayüzü**: animasyonlu Canvas arka planlı 9 sinematik tema, tam TR/EN i18n
- Apache Kafka ile **olay güdümlü**; Docker Compose ile **tamamen konteynerli**
- **Gözlemlenebilirlik**: Prometheus + Grafana + Loki, `/health` ve `/metrics`
- **343 test**, hepsi yeşil; GitHub Actions CI

---

### Mimari

NexStream, **Hexagonal Mimari (Ports & Adapters)** üzerine kuruludur. Domain katmanı dış sistemleri tanımaz; adapter'lar port'ları implemente eder, `dependencies.py` bunları bağlar. Bağımlılık yönü kesinlikle **Adapter → Application → Domain**'dir.

```
Zamanlayıcı (her 10 dk)
        |
        v
Kafka: news_updates  ──>  Kafka worker
                                |
            çek ──> RSS scraper (17 kaynak)
            analiz ─> Groq analyzer (duygu/varlık/konu/özet)
            skor ──> kalite + güvenilirlik + corroboration
            kaydet ─> PostgreSQL
            indexle ─> ChromaDB (embedding, dedup)
            bildir ─> WebSocket yayını + keyword alert
                                |
                                v
              Next.js arayüzü  ·  Public API v1  ·  RSS feed
```

---

### Haber Kaynakları (17)

**Türkçe (11):** TRT Haber, BBC Türkçe, Hürriyet, Hürriyet Spor, Sabah, CNN Türk, Sözcü, Habertürk, HT Spor, Anadolu Ajansı, AA Ekonomi
**İngilizce (6):** BBC Technology, BBC Sport, Guardian Tech, TechCrunch, Hacker News, The Verge

---

### Frontend (Next.js)

Streamlit panel, ayırt edici bir **sinematik tema sistemi** olan **Next.js 14 + React** arayüzüyle değiştirildi:

- **9 sinematik tema** — Matrix, Godfather, Blade Runner, Dune, Star Wars, Spider-Man, Batman, Wolfenstein + sade **Day** modu. Her tema; renk, font, tam ekran animasyonlu **Canvas arka plan** (dijital yağmur, film greni, neon yağmur, kum fırtınası, yıldız alanı, örümcek ağı, bat-signal, közler) ve geçişte bir flash efekti getirir. **Saf CSS + Canvas — görsel/video asset yok.**
- **Tema registry** (`lib/theme/registry.ts`): tek doğruluk noktası. Yeni tema = 1 kayıt + 1 CSS bloğu + 1 Canvas efekti, tüketici kodu değişmez (Open/Closed). Tüm efektler tek `requestAnimationFrame` döngüsünü paylaşır (`useCanvasScene`).
- **Tam TR / EN i18n**: tüm metinler `lib/i18n.ts`'te; landing, dashboard, hesap ve admin sayfaları birlikte dil değiştirir.
- `prefers-reduced-motion`'a saygı gösterir; sekme gizliyken animasyonları duraklatır.

---

### Hızlı Başlangıç

```bash
# 1. Repoyu klonla
git clone https://github.com/MaviMakumba/NexStream-News-Engine.git
cd NexStream-News-Engine

# 2. Ortam dosyasını oluştur ve Groq anahtarını ekle
cp .env.example .env
# .env içine: GROQ_API_KEY=gsk_xxxxxxxxxxxxxxxxxxxx

# 3. Tüm yığını başlat
docker compose up -d
```

Konteynerler ayağa kalktıktan sonra `http://localhost:3000` arayüzünü aç. Scheduler her 10 dakikada bir scrape'i otomatik tetikler, Kafka worker haberleri AI analizinden geçirir — manuel işlem gerekmez. `http://localhost:8000/health` ile DB / Kafka / ChromaDB'nin yeşil olduğunu doğrula.

> **Temiz aç/kapa:** `docker compose down` ardından `docker compose up -d`. Kafka, Zookeeper ve ChromaDB `restart: unless-stopped` ile çalışır; ani kapanışta bile yığın kendini toparlar.

#### Frontend geliştirme (Docker dışı, opsiyonel)

```bash
cd frontend
npm install
npm run dev      # http://localhost:3000 (hot reload)
npm run build    # tip kontrolü + prod build
```

---

### Testleri Çalıştırma

```bash
pip install -r requirements.txt
python -m pytest tests/ -v
```

**343 test** — domain, application ve adapter katmanları. Her dış çağrı (Groq, Kafka, DB, ChromaDB) mock'lanır; ağ erişimi gerekmez.

---

### Ortam Değişkenleri

| Değişken | Açıklama |
|----------|----------|
| `GROQ_API_KEY` | Groq API anahtarı (zorunlu) |
| `HUGGINGFACE_API_KEY` | Opsiyonel analyzer yedeği (boşsa devre dışı) |
| `DB_*`, `CHROMA_*`, `KAFKA_BOOTSTRAP_SERVERS` | Bağlantılar |
| `REDIS_URL` | Redis cache (boşsa null-cache) |
| `API_KEY` | Paylaşımlı admin/bakım anahtarı (varsayılan `dev-key-change-me`) |
| `SESSION_TTL_DAYS` | Session süresi (30) |
| `RESEND_API_KEY` | E-posta bülteni (boşsa console adapter) |
| `STRIPE_*` | Stripe ödeme (yoksa `/billing/*` → 503) |

---

### Katkıda Bulunma

Conventional Commits kullanılır: `feat:`, `fix:`, `chore:`, `ci:`, `refactor:`, `test:`, `docs:`.

---

### Yol Haritası

| Sürüm | Odak | Durum |
|-------|------|-------|
| v1.2 | Hibrit arama, 11 kaynak, dashboard, health | ✅ |
| v1.3 | Sertleştirme: Settings, logging, auth, rate limit, CORS | ✅ |
| v1.4 | Performans: async scrape, batch, index'ler, pub_date | ✅ |
| v1.5 | AI: NER, konu, trending, semantik dedup, reanalyze | ✅ |
| v1.6 | Production: Nginx + HTTPS, Prometheus + Grafana + Loki, backup | ✅ |
| v1.7 | WebSocket, bülten + keyword alert, public API v1, RSS, abonelik | ✅ |
| v1.8 | 17 kaynak, ilişki grafı, kalite + güvenilirlik skoru, LLM fallback | ✅ |
| v1.9 | Kullanıcı hesapları, katmanlı API, analytics, Stripe, Redis, sponsor | ✅ |
| v1.10 | Sinematik tema Next.js frontend (9 tema), tam i18n, Kafka dayanıklılığı | ✅ |
| v2.0 | Public launch: domain + VPS, landing SEO, API docs portalı, Product Hunt | 🔜 |

---

<div align="center">

**NexStream** · Python · FastAPI · Kafka · Groq · ChromaDB · Next.js

</div>
