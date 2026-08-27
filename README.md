<div align="center">

# NexStream News Engine

**AI-Powered Multi-Source News Intelligence Platform**

[![Tests](https://github.com/MaviMakumba/NexStream-News-Engine/actions/workflows/tests.yml/badge.svg)](https://github.com/MaviMakumba/NexStream-News-Engine/actions/workflows/tests.yml)
![Python](https://img.shields.io/badge/Python-3.11-blue?logo=python)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?logo=fastapi)
![Next.js](https://img.shields.io/badge/Next.js-14-000000?logo=nextdotjs)
![Redpanda](https://img.shields.io/badge/Redpanda-Kafka--compatible-E33237)
![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker)
![Tests](https://img.shields.io/badge/tests-837_passing-brightgreen)
![PWA](https://img.shields.io/badge/PWA-installable-5A0FC8?logo=pwa)
![License](https://img.shields.io/badge/License-MIT-green)

### 🚀 Live demo: **[nexstreamnewsengine.duckdns.org](https://nexstreamnewsengine.duckdns.org)**

<sub>Running on a single AWS t3.small (2 vCPU / 1.9 GB) — the full 16-service production stack, observability included.</sub>

[English](#english) · [Türkçe](#turkce)

</div>

---

<a name="english"></a>
## English

### Overview

NexStream is an event-driven news aggregation and intelligence platform. It continuously collects articles from **17 sources** in Turkish and English, runs them through an AI pipeline (sentiment, named-entity recognition, topic classification, summarization, plus quality and source-credibility scoring), enables hybrid semantic + keyword search, and surfaces everything through a **Next.js frontend with a cinematic, multi-theme UI**.

What started as a course project on enterprise architecture has grown into a production-shaped SaaS: user accounts with email verification, a **genuinely tier-gated** public API with usage metering, Stripe billing, a real-time WebSocket feed with per-connection limits, email newsletters, a full observability stack, and a security-hardened deployment path (rate limiting, secret rotation discipline, prod-config guardrails, automated dependency updates).

**Key capabilities:**
- **17 sources** (11 Turkish + 6 English), added declaratively via a scraper registry
- **AI pipeline** on Groq `openai/gpt-oss-20b`: sentiment + entities (people/orgs/locations) + topic + summary in a single prompt, with an optional Hugging Face fallback
- **Hybrid search**: ChromaDB semantic vectors + PostgreSQL keyword, combined-score ranked with recency decay, Turkish morphological stemming
- **Trending engine**, **related-article graph** (entity overlap, Pro+), **story clusters** ("who's covering this story", semantic similarity, free for everyone), and **semantic dedup**
- **Evidence-grounded RAG Q&A** ("ask about this story"): a dedicated `QuestionAnsweringPort`, a deterministic evidence gate (no LLM call at all below a retrieval-confidence threshold), and a hard cap of one Groq call per question
- **Quality + credibility scoring**: deterministic content-quality score and source-credibility / corroboration metrics
- **Reader features**: save-for-later bookmarks, estimated reading time, in-browser text-to-speech (Web Speech API, free)
- **Moderation**: role-based user banning (`is_active` toggle, session revocation) alongside the role hierarchy
- **Real-time WebSocket feed** (Pro+, per-user + global connection caps), **email newsletter + instant keyword alerts + web push notifications**, **RSS/Atom feed**
- **Error tracking + product analytics**: Sentry (backend) and PostHog (frontend), both no-op when unconfigured
- **Fully automated CI/CD**: every merge to `main` that passes tests redeploys to production and verifies `/health` — no manual deploy step
- **User accounts** with email verification, session auth (HttpOnly cookies), **tiered API** (Free / Pro / Enterprise) with per-user rate limits, per-tier search-result caps, and usage analytics
- **Stripe billing** (with a no-Stripe dev mode for local demos), **raw data export** (CSV/JSON, Enterprise-only), **Redis cache**
- **Role-based admin** (user / moderator / admin hierarchy + `ADMIN_EMAILS` bootstrap), **self-service usage dashboard**, and **personal API keys** (`X-User-Key`) for the public API
- **Next.js 14 frontend**: 9 cinematic themes with animated Canvas backgrounds (low/high performance profiles), full TR/EN i18n, WCAG AA-checked contrast, installable **PWA**
- **Event-driven** via Redpanda (Kafka-compatible, ARM-friendly); **fully containerized** with Docker Compose
- **Observability**: Prometheus + Grafana + Loki, `/health` and `/metrics` endpoints
- **Security-hardened**: prod-startup config guard, timing-safe auth checks, HTML-escaped emails, per-route rate limits, encrypted + offsite-capable backups
- **837 tests**, all green; CI via GitHub Actions with Dependabot-driven dependency updates

**At a glance:**

| Metric | Value |
|--------|-------|
| News sources | 17 (11 Turkish + 6 English) |
| Backend tests | 837 — all green |
| API endpoints | 60, across 11 routers |
| Cinematic frontend themes | 9 |
| API tiers | 3 (Free / Pro / Enterprise) — server-enforced |
| Docker services | 10 (dev) / 16 (prod, incl. observability stack) |
| Architecture | Hexagonal (Ports & Adapters), 3 layers |

---

### Screenshots

| Landing — Matrix theme | Landing — Star Wars theme |
|---|---|
| ![Landing page in the Matrix theme](docs/screenshots/landing.png) | ![Landing page in the Star Wars theme](docs/screenshots/landing-starwars-theme.png) |

| Dashboard (live data, trending, tier badges) | Semantic search (match % per result) |
|---|---|
| ![Dashboard with trending topics and news feed](docs/screenshots/dashboard.png) | ![Semantic search results with match percentages](docs/screenshots/search.png) |

![Theme picker showing the 9 cinematic themes](docs/screenshots/theme-picker.png)
<p align="center"><sub>All screenshots taken from a live local run against real scraped data.</sub></p>

---

### Architecture

NexStream is built on **Hexagonal Architecture (Ports & Adapters)**. The domain layer has zero knowledge of external systems; adapters implement ports and are wired together in `dependencies.py`. Dependency direction is strictly **Adapter → Application → Domain**.

```mermaid
flowchart TB
    subgraph Domain["Domain Layer — zero external dependencies"]
        D1["Article Model"]
        D2["Ports (ABCs)"]
        D3["Pydantic Schemas"]
        D4["Pure Scoring"]
    end
    subgraph Application["Application Layer"]
        A1["NewsService<br/>orchestration + metadata enrichment"]
    end
    subgraph Adapters["Adapters Layer"]
        AD1["Scrapers<br/>17 RSS feeds"]
        AD2["Analyzer<br/>Groq + HF fallback"]
        AD3["Repository<br/>PostgreSQL"]
        AD4["API<br/>FastAPI REST + v1"]
        AD5["Messaging<br/>Redpanda"]
        AD6["Scheduling<br/>APScheduler"]
        AD7["Vector Search<br/>ChromaDB"]
        AD8["Auth<br/>Session + tiers"]
        AD9["Embedder<br/>HTTP → model service"]
    end
    Adapters --> Application --> Domain
```

**Event flow:**

```mermaid
flowchart LR
    SCHED["Scheduler<br/>every 10 min"] --> TOPIC[("Redpanda<br/>news_updates")]
    TOPIC --> WORKER["Kafka-compatible<br/>Worker"]
    WORKER --> FETCH["Fetch<br/>RSS scraper (17 sources)"]
    FETCH --> ANALYZE["Analyze<br/>Groq: sentiment/NER/topic"]
    ANALYZE --> SCORE["Score<br/>quality + credibility"]
    SCORE --> DB[("PostgreSQL")]
    SCORE --> EMB["Embedder service<br/>model, single copy"]
    EMB --> VEC[("ChromaDB")]
    DB --> NOTIFY["Notify<br/>WebSocket + keyword alerts"]
    VEC --> NOTIFY
    NOTIFY --> FE["Next.js Frontend"]
    NOTIFY --> API1["Public API v1"]
    NOTIFY --> RSS["RSS Feed"]
```

---

### Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Next.js 14 + React + TypeScript — 9 cinematic themes (pure CSS + Canvas), installable PWA |
| API | FastAPI + Uvicorn (REST + versioned `/api/v1`) |
| Auth & limits | Session tokens (bcrypt), slowapi rate limiting, per-tier quotas |
| Message broker | Redpanda (Kafka-compatible, single-node) |
| AI analyzer | Groq `openai/gpt-oss-20b` (+ optional Hugging Face fallback) |
| Embeddings | `paraphrase-multilingual-MiniLM-L12-v2` (local, no API key) |
| Vector search | ChromaDB (persistent) |
| Database | PostgreSQL 15 + SQLAlchemy ORM |
| Cache | Redis 7 (sessions / trending; null-cache fallback) |
| Payments | Stripe (Checkout + webhook + billing portal) |
| Email | SMTP (Gmail) primary, Resend API fallback, console adapter for dev |
| Scheduler | APScheduler |
| Observability | Prometheus + Grafana (provisioned alerting) + Loki + Promtail |
| Reverse proxy | Nginx + Let's Encrypt (production) |
| Containerization | Docker + Docker Compose |
| CI/CD | GitHub Actions |
| Testing | pytest (837 tests, ~33s) |
| Dependency updates | Dependabot (pip + npm + GitHub Actions, weekly) |

---

### How It Works — Scoring & Search Algorithms

The interesting parts of this project aren't "call an LLM" — they're what happens around
it: deterministic scoring that costs no API calls, a search ranking formula that
blends two very different retrieval methods, and the bugs found (and fixed) by
actually measuring the results instead of assuming they were correct.

**Sentiment + entities + topic + summary — one Groq call per article.** A single
prompt asks for all four at once (not four separate calls): a sentiment score in
`[-1.0, 1.0]` mapped to Positive/Negative/Neutral at the `±0.2` thresholds, named
entities (persons/organizations/locations), a topic classification, and a 1-2
sentence summary in the article's own language. Model: `openai/gpt-oss-20b` on
Groq's free tier — swapped in August 2026 after Groq fully retired the previous
model (`llama-3.1-8b-instant`), which silently degraded every analysis to a
neutral default for about a day before anyone noticed (the fail-open design that
keeps the pipeline from crashing on a bad API response also means a dead model
doesn't announce itself — worth knowing if you build on top of an LLM API you
don't control).

**Quality score — no LLM, fully deterministic.** A weighted sum of four signals,
computed in pure Python (`domain/scoring/quality.py`), each capped at its own weight:

```
quality = 0.40 · min(content_length / 600, 1)       # longer articles score higher, capped
        + 0.35 · min(entity_count / 5, 1)            # more named entities = more substantive
        + 0.15 · (1 if summary_len >= 20 else 0)      # has a real summary
        + 0.10 · (1 if 15 <= title_len <= 200 else 0) # sane title length
```

**Credibility score — a base rating plus cross-source corroboration.** Each source
has a hand-seeded base credibility (`domain/scoring/credibility.py`, 0.50–0.90,
e.g. BBC 0.90, Hacker News 0.60) that nudges up by `0.05` per *independent* source
reporting overlapping entities for the same story (capped at `+0.20`) — a rough
approximation of "did more than one outlet cover this."

**Hybrid search — semantic + keyword, blended and recency-weighted.**
`hybrid_search()` runs a ChromaDB vector query and a PostgreSQL keyword query in
parallel, scores each candidate as `max(semantic_score, keyword_score)` with a
`+0.10` bonus for articles that hit *both*, then multiplies the result by a
recency factor (today = ×1.0, decaying linearly to ×0.5 at the 30-day mark). The
keyword side does coverage scoring per field (title `0.9` > summary `0.7` >
content `0.5`) with basic Turkish suffix-stripping for recall (`"beşiktaşın"`
also matches `"Beşiktaş"`). **A real bug found this way, in production, on 18
Aug 2026:** the stemmer added *both* the raw word and its stem as separate terms
in the coverage denominator, so any single-word query with a Turkish suffix had
its score cut roughly in half — enough to fall below ChromaDB's noise floor and
get pushed out of the results entirely by unrelated matches. Fixed by scoring
against canonical (stem-only) terms while still searching Postgres with the
wider raw+stem set.

**Semantic deduplication.** Before indexing, a new article's embedding is
compared against ChromaDB's existing vectors; anything above a `0.92` cosine
similarity threshold is flagged as a near-duplicate rather than indexed twice.

**RAG Q&A — deterministic evidence gate, not "ask the LLM and hope."** Before
`POST /api/v1/news/ask` spends a single Groq call, retrieval runs first and the
top-scoring candidates are checked against a confidence threshold in plain
Python; if nothing clears it, the endpoint returns a "no evidence found"
response without ever touching the LLM. When it does call Groq, the prompt
carries the retrieved articles' text as explicitly-labeled *data* (not
instructions — a lightweight prompt-injection mitigation, since article
content is technically untrusted external input), and the model must cite
which numbered source(s) it used. Found and fixed through actual production
QA rather than only unit tests: a synchronous HTTP request that copied a
background worker's "wait out the rate limit" retry pattern, leaving users
staring at a spinner for minutes until it was changed to fail fast instead.

**Measured, not claimed** (pulled from the live Prometheus instance, not
estimated): Groq analysis latency averages **~0.5s**, p95 **~2.1s** per article.
17 sources scraped every 10 minutes, ~25 articles/source/run. Moving the
embedding model into its own service cut the `app`/`worker` Docker images from
1.55GB to **516MB** and startup from 1-2 minutes to **~6 seconds**. The test
suite (837 tests) runs in **~33 seconds**, down from ~400s after finding and
fixing a test fixture that was silently attempting a real (2-second-timeout)
database connection on every request.

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
| POST | `/api/v1/news/search` | Hybrid semantic + keyword search, result cap by tier (Free 10 / Pro 50 / Enterprise 200) |
| GET | `/api/v1/news/trending` | Trending entities (last N hours) |
| GET | `/api/v1/news/{id}/related` | Related articles via entity overlap (Pro+) |
| GET | `/api/v1/news/{id}/sources` | Story cluster — who else is covering this story (free) |
| POST | `/api/v1/news/ask` | Evidence-grounded RAG Q&A, general or article-specific |
| GET | `/api/v1/news/export` | Raw data export, CSV or JSON (Enterprise-only) |
| GET | `/api/v1/news/sources` | Registered sources |
| POST | `/auth/register` · `/auth/login` · `/auth/logout` | Session-based auth (HttpOnly cookie) |
| POST | `/auth/resend-verification` · `/auth/verify-email` | Email verification flow |
| POST | `/auth/forgot-password` · `/auth/reset-password` | Password reset |
| GET/POST/DELETE | `/account/api-key` | Personal `X-User-Key` API key management |
| GET/POST/PATCH/DELETE | `/subscriptions` | Newsletter / keyword-alert preferences |
| POST | `/billing/checkout` · `/billing/portal` | Stripe Checkout & billing portal |
| GET | `/admin/users` · `/admin/usage` · `/admin/sponsors` | Admin analytics, user/role & sponsor management |
| GET | `/feed.xml` | RSS/Atom feed |
| WS | `/ws/feed` | Real-time article stream (Pro+, per-user + global connection caps) |
| POST | `/news/scrape` · `/news/reindex` · `/news/reanalyze` | Maintenance (`X-API-Key`) |
| GET | `/health` · `/metrics` | Health (DB/Redpanda/ChromaDB) · Prometheus metrics |
| GET | `/docs` | Swagger UI |

**Full interactive reference:** [nexstreamnewsengine.duckdns.org/api/docs](https://nexstreamnewsengine.duckdns.org/api/docs) — every endpoint, request/response schema, and a "Try it out" button. A ready-to-import [Postman collection](docs/NexStream.postman_collection.json) covers the endpoints above with example requests.

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

Once all containers are healthy, open the frontend at `http://localhost:3000`. The scheduler triggers scraping every 10 minutes and the Kafka-compatible worker processes articles through the AI analyzer automatically — no manual action needed. Confirm `http://localhost:8000/health` shows DB, Kafka, ChromaDB and the embedder service all green. The embedding model is baked into the `embedder` image at build time, so there is no first-run download — `app` and `worker` simply wait for the embedder to finish loading it from disk (~30-60s).

> **Clean start/stop:** use `docker compose down` then `docker compose up -d`. Redpanda and ChromaDB run with `restart: unless-stopped`, so the stack self-heals even after an abrupt shutdown.

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

**Test coverage: 837 tests** across domain, application, and adapter layers. Every external call (Groq, Kafka, DB, ChromaDB, SMTP/Resend) is mocked — no network access, no real emails sent — required.

<details>
<summary>Actual local run output</summary>

```
$ python -m pytest tests/ -q
........................................................................ [  8%]
........................................................................ [ 17%]
........................................................................ [ 25%]
........................................................................ [ 34%]
........................................................................ [ 43%]
........................................................................ [ 51%]
........................................................................ [ 60%]
........................................................................ [ 68%]
........................................................................ [ 77%]
........................................................................ [ 86%]
........................................................................ [ 94%]
.............................................                            [100%]
837 passed, 1 warning in 32.76s
```

</details>

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
| `EMBEDDER_URL` | Embedding service — the model lives there as a single copy, `app`/`worker` ask over HTTP | `http://embedder:8000` |
| `EMBEDDER_MODE` | `http` (default) or `local` (loads the model in-process; Docker-less development only) | `http` |
| `KAFKA_BOOTSTRAP_SERVERS` | Kafka-compatible broker (Redpanda) | `redpanda:29092` |
| `REDIS_URL` | Redis cache (null-cache if empty) | `redis://redis:6379/0` |
| `API_KEY` | Shared admin/maintenance key | `dev-key-change-me` |
| `SESSION_TTL_DAYS` | Session token lifetime | `30` |
| `CORS_ORIGINS` | Allowed origins | `http://localhost:3000,...` |
| `RESEND_API_KEY` | Email newsletter (console adapter if empty) | — |
| `STRIPE_SECRET_KEY` / `STRIPE_WEBHOOK_SECRET` | Stripe billing (`/billing/*` returns 503 if unset) | — |
| `STRIPE_PRO_PRICE_ID` / `STRIPE_ENTERPRISE_PRICE_ID` | Stripe price IDs | — |
| `BILLING_DEV_MODE` | Skip Stripe, upgrade tiers instantly (local demo only — never in production) | `false` |
| `ADMIN_EMAILS` | Comma-separated emails bootstrapped as admin, no DB write needed | — |
| `OWNER_EMAILS` | Comma-separated emails bootstrapped as owner (Enterprise-equivalent access, never assignable via API) | — |
| `EMAIL_PROVIDER` | `auto` (SMTP if configured, else Resend, else console) / `smtp` / `resend` / `console` | `auto` |
| `SMTP_HOST` / `SMTP_PORT` / `SMTP_USER` / `SMTP_PASSWORD` | Transactional email via SMTP (e.g. Gmail — use an app password, not your login password) | `smtp.gmail.com` / `587` / … |
| `ENVIRONMENT` | `production` enables a startup guard that refuses to boot with an unsafe config (default API key, `CORS_ORIGINS=*`, dev billing mode, insecure cookies) | `development` |
| `EXPORT_MAX_ROWS` | Row ceiling for the raw data export endpoint | `20000` |
| `WS_MAX_CONNECTIONS_PER_USER` / `WS_MAX_TOTAL_CONNECTIONS` | `/ws/feed` per-user / global connection caps | `5` / `500` |
| `RAG_RETRIEVAL_THRESHOLD` | Minimum retrieval confidence before `/news/ask` calls the LLM at all | `0.4` |
| `VAPID_PUBLIC_KEY` / `VAPID_PRIVATE_KEY` | Web push notifications (disabled if empty) | — |
| `SENTRY_DSN` | Backend error tracking, `app` + `worker` (no-op if empty) | — |
| `NEXT_PUBLIC_POSTHOG_KEY` | Frontend product analytics (no-op if empty) | — |
| `BACKUP_GPG_PASSPHRASE` | Encrypts backups with GPG AES256 if set (see `infra/backup/`) | — |
| `RCLONE_REMOTE` | Offsite backup upload target (e.g. `b2:my-bucket`) if set | — |

---

### API Tiers

| Tier | Price | Daily API quota | Search result cap | Highlights |
|------|-------|-----------------|--------------------|------------|
| Free | $0 | 100 requests | 10 results | News & semantic search, daily digest |
| Pro | $9.99 / mo | 2,000 requests | 50 results | WebSocket live feed, keyword alerts, related-article graph |
| Enterprise | $49.99 / mo | Unlimited | 200 results | Raw data export (CSV/JSON), custom sources, SLA, priority support |

> All of the above are **actually enforced server-side**, not just marketing copy — see `TIER_SEARCH_RESULT_CAP` and the `tier_at_least()` checks on `/ws/feed`, `/news/{id}/related`, and `/news/export`. Billing requires Stripe configuration; without it the upgrade endpoints intentionally return `503` (or `BILLING_DEV_MODE=true` for a no-Stripe local demo). Admin endpoints accept either the shared `API_KEY` or an admin/moderator user session.

---

### CI/CD

Every push / PR to `main` triggers GitHub Actions:

1. Spins up a PostgreSQL 15 service container
2. Installs Python dependencies (incl. `pytest-asyncio`)
3. Runs all 837 tests with `pytest`
4. Reports pass/fail status
5. **On `main` only, if tests pass:** connects to the production instance over AWS SSM, pulls and rebuilds, then polls `/api/health` to confirm the new version is actually up — a merge to `main` reaches production with no manual step

Dependabot also opens weekly PRs for pip, npm, and GitHub Actions dependency updates (review/merge/rebuild stays manual by design — no auto-merge).

---

### Contributing

Uses Conventional Commits: `feat:`, `fix:`, `chore:`, `ci:`, `refactor:`, `test:`, `docs:`.

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
| v1.11 | Billing dev mode, role-based admin, self-service usage panel, personal API keys, project-wide clean-code pass | ✅ Done |
| v1.12 | Responsive UI, WCAG AA accessibility, SEO, theme performance profiles | ✅ Done |
| v1.13 | Role hierarchy (user / moderator / admin) | ✅ Done |
| v1.14 | Tier-gating actually enforced server-side (search caps, related graph, live feed) | ✅ Done |
| v1.15 | Email verification flow | ✅ Done |
| v1.16 | Raw data export (Enterprise), live dashboard feed injection | ✅ Done |
| v1.17 | Full security audit & hardening (auth, injection, secrets, DoS, dependencies) | ✅ Done |
| v1.18 | Kafka→Redpanda migration (ARM-ready), installable PWA, Dependabot, encrypted/offsite backups, WebSocket connection caps | ✅ Done |
| v1.19 | Closed the last known rate-limit gap on the public search endpoint | ✅ Done |
| v2.0 | Public launch: RAM-optimized deploy to a free-tier cloud VPS, real domain + TLS | ✅ Done |
| v2.1 | Owner role, tiered role management, real transactional email (SMTP) | ✅ Done |
| v2.1.1 | Live security review: Groq model swap, WebSocket fix, nginx header fix, Turkish search-scoring fix, `main` sync | ✅ Done |
| v2.2–v2.3 | Search query expansion (related terms via Groq), save-for-later, corroboration badges, browser-native TTS, story clusters, moderator user bans, sortable admin tables | ✅ Done |
| v2.4 | Error tracking + product analytics: Sentry (backend) and PostHog (frontend), both fully optional | ✅ Done |
| v2.5 | Web push notifications, sharing the existing keyword-alert matching as a second delivery channel | ✅ Done |
| v2.6 | Evidence-grounded RAG Q&A (`/api/v1/news/ask`) — deterministic evidence gate, one Groq call per question max | ✅ Done |
| Next up | Fetching full article text on-demand for richer Q&A evidence, a trust/relevance scoring pass, homepage redesign | 🔜 Planned |

*Real Stripe billing stays deliberately deferred — the code path is ready, but ad-supported free tier is the current monetization direction (see the "How It Works" section above for the engineering rationale behind most other decisions; product/business calls like this one are tracked internally rather than in this table).*

---

### License

MIT License — see [LICENSE](LICENSE) for details.

---

<a name="turkce"></a>
## Türkçe

### Genel Bakış

NexStream, **17 kaynaktan** Türkçe ve İngilizce haber toplayan, bunları bir yapay zeka hattından (duygu, varlık tanıma, konu sınıflandırma, özetleme + kalite ve kaynak güvenilirliği skorlaması) geçiren, hibrit anlamsal + anahtar kelime araması sunan ve her şeyi **sinematik, çok temalı bir Next.js arayüzünde** gösteren olay güdümlü bir haber platformudur.

Kurumsal mimari dersi için başlayan proje; e-posta doğrulamalı kullanıcı hesapları, **gerçekten kilitli** katmanlı bir API, Stripe ödeme, bağlantı limitli gerçek zamanlı WebSocket akışı, e-posta bülteni, tam bir gözlemlenebilirlik yığını ve sertleştirilmiş bir deploy yolu (rate limiting, secret rotasyon disiplini, prod-config guard'ı, otomatik bağımlılık güncellemeleri) ile production'a yakın bir SaaS'a dönüştü.

**Temel özellikler:**
- **17 kaynak** (11 TR + 6 EN), scraper registry ile bildirimsel eklenir
- **AI hattı** (Groq `openai/gpt-oss-20b`): tek prompt'ta duygu + varlıklar (kişi/kurum/yer) + konu + özet; opsiyonel Hugging Face yedeği
- **Hibrit arama**: ChromaDB anlam vektörü + PostgreSQL anahtar kelime, recency decay'li birleşik skor; Türkçe morfolojik kök ayıklama
- **Trending motoru**, **ilişki grafı** (varlık örtüşmesi, Pro+), **story cluster** ("bu haberi kim nasıl anlatıyor", semantik benzerlik, herkese ücretsiz) ve **anlamsal dedup**
- **Kanıta dayalı RAG soru-cevap** ("bu haber hakkında sor"): ayrı bir `QuestionAnsweringPort`, deterministik kanıt kapısı (retrieval güveni eşiğin altındaysa LLM'e hiç gidilmez), soru başına en fazla 1 Groq çağrısı
- **Kalite + güvenilirlik skorlaması**: deterministik içerik kalitesi + kaynak güvenilirliği / doğrulama metrikleri
- **Okuyucu özellikleri**: kaydet/sonra oku, okuma süresi tahmini, tarayıcı-içi sesli okuma (Web Speech API, ücretsiz)
- **Moderasyon**: rol hiyerarşisinin yanında kullanıcı banlama (`is_active` toggle, oturum iptali)
- **Gerçek zamanlı WebSocket akışı** (Pro+, kullanıcı başına + toplam bağlantı tavanı), **e-posta bülteni + anlık keyword alert + web push bildirimleri**, **RSS/Atom feed**
- **Hata takibi + ürün analytics**: Sentry (backend) ve PostHog (frontend), ikisi de yapılandırılmazsa tamamen devre dışı
- **Tam otomatik CI/CD**: testleri geçen her `main` merge'i otomatik prod'a deploy olur ve `/health`'i doğrular — elle deploy adımı yok
- **Kullanıcı hesapları** e-posta doğrulamalı, session auth (HttpOnly cookie), **katmanlı API** (Free / Pro / Enterprise) kullanıcı bazlı limit + arama sonucu tavanı + analytics
- **Stripe ödeme** (lokal demo için Stripe'sız dev mode), **ham veri export** (CSV/JSON, sadece Enterprise), **Redis cache**
- **Rol tabanlı admin** (user / moderator / admin hiyerarşisi + `ADMIN_EMAILS` bootstrap), **self-service kullanım paneli**, public API için **kişisel API anahtarı** (`X-User-Key`)
- **Next.js 14 arayüzü**: animasyonlu Canvas arka planlı 9 sinematik tema (düşük/yüksek performans profili), tam TR/EN i18n, WCAG AA kontrast denetimli, kurulabilir **PWA**
- Redpanda (Kafka-uyumlu, ARM-dostu) ile **olay güdümlü**; Docker Compose ile **tamamen konteynerli**
- **Gözlemlenebilirlik**: Prometheus + Grafana + Loki, `/health` ve `/metrics`
- **Güvenlik sertleştirmesi**: prod-açılış config guard'ı, zamanlama-güvenli auth kontrolleri, HTML-escape'li e-postalar, route-bazlı rate limit'ler, şifrelenebilir + offsite yedekleme
- **837 test**, hepsi yeşil; GitHub Actions CI + Dependabot ile otomatik bağımlılık güncellemesi

**Bir bakışta:**

| Metrik | Değer |
|--------|-------|
| Haber kaynağı | 17 (11 TR + 6 EN) |
| Backend test | 837 — hepsi yeşil |
| API endpoint'i | 60, 11 router’da |
| Sinematik frontend teması | 9 |
| API katmanı | 3 (Free / Pro / Enterprise) — sunucu tarafında zorunlu |
| Docker servisi | 10 (dev) / 16 (prod, gözlemlenebilirlik yığını dahil) |
| Mimari | Hexagonal (Ports & Adapters), 3 katman |

---

### Ekran Görüntüleri

| Landing — Matrix teması | Landing — Star Wars teması |
|---|---|
| ![Matrix temasında landing sayfası](docs/screenshots/landing.png) | ![Star Wars temasında landing sayfası](docs/screenshots/landing-starwars-theme.png) |

| Dashboard (canlı veri, trend olan konular, tier rozetleri) | Anlamsal arama (sonuç başına eşleşme %'si) |
|---|---|
| ![Trend konular ve haber akışlı dashboard](docs/screenshots/dashboard.png) | ![Eşleşme yüzdeli anlamsal arama sonuçları](docs/screenshots/search.png) |

![9 sinematik temayı gösteren tema seçici](docs/screenshots/theme-picker.png)
<p align="center"><sub>Tüm ekran görüntüleri, gerçek scrape edilmiş veri üzerinden canlı bir lokal çalıştırmadan alındı.</sub></p>

---

### Mimari

NexStream, **Hexagonal Mimari (Ports & Adapters)** üzerine kuruludur. Domain katmanı dış sistemleri tanımaz; adapter'lar port'ları implemente eder, `dependencies.py` bunları bağlar. Bağımlılık yönü kesinlikle **Adapter → Application → Domain**'dir.

```mermaid
flowchart TB
    subgraph Domain["Domain Katmanı — dış bağımlılık yok"]
        D1["Article Modeli"]
        D2["Port'lar (ABC)"]
        D3["Pydantic Şemaları"]
        D4["Saf Skorlama"]
    end
    subgraph Application["Application Katmanı"]
        A1["NewsService<br/>orkestrasyon + metadata zenginleştirme"]
    end
    subgraph Adapters["Adapters Katmanı"]
        AD1["Scraper'lar<br/>17 RSS kaynağı"]
        AD2["Analyzer<br/>Groq + HF yedek"]
        AD3["Repository<br/>PostgreSQL"]
        AD4["API<br/>FastAPI REST + v1"]
        AD5["Messaging<br/>Redpanda"]
        AD6["Scheduling<br/>APScheduler"]
        AD7["Vector Search<br/>ChromaDB"]
        AD8["Auth<br/>Session + tier'lar"]
        AD9["Embedder<br/>HTTP → model servisi"]
    end
    Adapters --> Application --> Domain
```

**Olay akışı:**

```mermaid
flowchart LR
    SCHED["Zamanlayıcı<br/>her 10 dk"] --> TOPIC[("Redpanda<br/>news_updates")]
    TOPIC --> WORKER["Kafka-uyumlu<br/>Worker"]
    WORKER --> FETCH["Çek<br/>RSS scraper (17 kaynak)"]
    FETCH --> ANALYZE["Analiz et<br/>Groq: duygu/varlık/konu"]
    ANALYZE --> SCORE["Skorla<br/>kalite + güvenilirlik"]
    SCORE --> DB[("PostgreSQL")]
    SCORE --> EMB["Embedder servisi<br/>model, tek kopya"]
    EMB --> VEC[("ChromaDB")]
    DB --> NOTIFY["Bildir<br/>WebSocket + keyword alert"]
    VEC --> NOTIFY
    NOTIFY --> FE["Next.js Arayüzü"]
    NOTIFY --> API1["Public API v1"]
    NOTIFY --> RSS["RSS Feed"]
```

---

### Teknoloji Yığını

| Katman | Teknoloji |
|--------|-----------|
| Frontend | Next.js 14 + React + TypeScript — 9 sinematik tema (saf CSS + Canvas), kurulabilir PWA |
| API | FastAPI + Uvicorn (REST + sürümlü `/api/v1`) |
| Auth & limit | Session token (bcrypt), slowapi rate limiting, tier bazlı kota |
| Mesaj kuyruğu | Redpanda (Kafka-uyumlu, tek node) |
| AI analyzer | Groq `openai/gpt-oss-20b` (+ opsiyonel Hugging Face yedeği) |
| Embedding | `paraphrase-multilingual-MiniLM-L12-v2` (lokal, API key gerekmez) |
| Vektör arama | ChromaDB (persistent) |
| Veritabanı | PostgreSQL 15 + SQLAlchemy ORM |
| Cache | Redis 7 (session / trending; boşsa null-cache) |
| Ödeme | Stripe (Checkout + webhook + billing portal) |
| E-posta | SMTP (Gmail) birincil, Resend API yedek, dev'de console adapter |
| Zamanlayıcı | APScheduler |
| Gözlemlenebilirlik | Prometheus + Grafana (provisioned alerting) + Loki + Promtail |
| Reverse proxy | Nginx + Let's Encrypt (production) |
| Konteynerleştirme | Docker + Docker Compose |
| CI/CD | GitHub Actions |
| Test | pytest (837 test, ~33sn) |
| Bağımlılık güncellemesi | Dependabot (pip + npm + GitHub Actions, haftalık) |

---

### Nasıl Çalışır — Skorlama & Arama Algoritmaları

Bu projenin ilginç kısmı "bir LLM'e sor" değil — onun etrafında olan şey: API çağrısı
gerektirmeyen deterministik skorlama, iki farklı arama yöntemini birleştiren bir
sıralama formülü, ve sonuçları GERÇEKTEN ÖLÇEREK bulunan (ve düzeltilen) bug'lar.

**Duygu + varlık + konu + özet — haber başına TEK Groq çağrısı.** Dört ayrı istek
yerine tek bir prompt hepsini birden istiyor: `[-1.0, 1.0]` aralığında bir duygu
skoru (`±0.2` eşiğinde Pozitif/Negatif/Nötr'e eşleniyor), varlıklar (kişi/kurum/yer),
konu sınıflandırması ve haberin kendi dilinde 1-2 cümlelik özet. Model: Groq'un
ücretsiz katmanındaki `openai/gpt-oss-20b` — Ağustos 2026'da, Groq önceki modeli
(`llama-3.1-8b-instant`) tamamen kaldırdıktan sonra değiştirildi; bu model kaybı
kimse fark etmeden ~1 gün boyunca HER analizi sessizce nötr varsayılana düşürdü
(pipeline'ın kötü bir API yanıtında çökmesini önleyen "hata yut, devam et" tasarımı,
aynı zamanda ölü bir modelin kendini hiç haber vermemesi anlamına da geliyor —
kontrolünde olmayan bir LLM API'sinin üzerine bir şey inşa ediyorsan bilmekte fayda var).

**Kalite skoru — LLM yok, tamamen deterministik.** Saf Python'da hesaplanan
(`domain/scoring/quality.py`), her biri kendi ağırlığında tavanlanan 4 sinyalin
ağırlıklı toplamı:

```
kalite = 0.40 · min(içerik_uzunluğu / 600, 1)     # uzun haber daha yüksek puan, tavanlı
       + 0.35 · min(varlık_sayısı / 5, 1)          # daha çok isimlendirilmiş varlık = daha dolu içerik
       + 0.15 · (özet_uzunluğu >= 20 ise 1, değilse 0)   # gerçek bir özet var mı
       + 0.10 · (15 <= başlık_uzunluğu <= 200 ise 1, değilse 0)  # makul başlık uzunluğu
```

**Güvenilirlik skoru — taban puan + çapraz kaynak doğrulaması.** Her kaynağın elle
belirlenmiş bir taban güvenilirliği var (`domain/scoring/credibility.py`, 0.50-0.90
arası — mesela BBC 0.90, Hacker News 0.60), aynı olayı (örtüşen varlıklarla) raporlayan
her BAĞIMSIZ kaynak için `+0.05` artıyor (en fazla `+0.20`) — "birden fazla mecra bunu
haber yaptı mı" sorusunun kaba bir yaklaşıklığı.

**Hibrit arama — semantik + anahtar kelime, tazelikle ağırlıklandırılmış.**
`hybrid_search()` ChromaDB'de bir vektör sorgusu ile PostgreSQL'de bir anahtar
kelime sorgusunu paralel çalıştırır, her adayı `max(semantik_skor, keyword_skor)`
olarak puanlar (ikisinde de eşleşene `+0.10` bonus), sonra sonucu bir tazelik
çarpanıyla çarpar (bugün = ×1.0, 30 gün sonunda lineer olarak ×0.5'e iner).
Anahtar kelime tarafı alan bazlı kapsama puanı kullanır (başlık `0.9` > özet `0.7`
> içerik `0.5`) ve geri çağırma için basit bir Türkçe ek kırpması yapar
(`"beşiktaşın"` da `"Beşiktaş"`i eşleştirir). **Bu yöntemle canlıda bulunan gerçek
bir bug (18 Ağu 2026):** kök ayıklayıcı, kapsama bölenine hem ham kelimeyi HEM
kökünü ayrı ayrı terim olarak ekliyordu, yani Türkçe ekli tek kelimelik her sorgu
skorunun kabaca yarısını kaybediyordu — bu da ChromaDB'nin gürültü tabanının altına
düşüp sonuçlardan tamamen elenmesine yetiyordu. Çözüm: Postgres'i hâlâ geniş
ham+kök kümesiyle ararken, puanlamayı sadece kanonik (kök) terimlere göre yapmak.

**Semantik tekrar tespiti.** İndekslemeden önce yeni bir haberin embedding'i
ChromaDB'deki mevcut vektörlerle karşılaştırılır; `0.92` kosinüs benzerliğinin
üzerindeki her şey iki kez indekslenmek yerine near-duplicate olarak işaretlenir.

**RAG soru-cevap — "LLM'e sor ve umut et" değil, deterministik bir kanıt kapısı.**
`POST /api/v1/news/ask` tek bir Groq çağrısı harcamadan önce retrieval çalışır
ve en yüksek skorlu adaylar saf Python'da bir güven eşiğine karşı kontrol
edilir; hiçbiri eşiği geçmezse endpoint LLM'e hiç dokunmadan "kanıt bulunamadı"
döner. Groq çağrılırsa, prompt'a giren makale metinleri açıkça "veri" olarak
etiketlenir (talimat değil — makale içeriği teknik olarak güvenilmeyen dış
girdi olduğu için hafif bir prompt-injection önlemi) ve model hangi numaralı
kaynağı/kaynakları kullandığını belirtmek zorundadır. Sadece unit testle değil
gerçek canlı QA ile bulunup düzeltilmiş bir örnek: senkron bir HTTP isteği,
bir arka plan worker'ının "rate limit'i sabırla bekle" retry desenini
kopyalamıştı — kullanıcı dakikalarca yükleniyor ekranında kalıyordu, fail-fast
davranışına çevrilince düzeldi.

**Tahmin değil, ÖLÇÜLMÜŞ** (canlı Prometheus'tan çekildi, tahmini değil): Groq
analiz gecikmesi ortalama **~0.5sn**, p95 **~2.1sn**/haber. 17 kaynak her 10
dakikada bir taranıyor, ~25 haber/kaynak/çalışma. Embedding modelini ayrı bir
servise taşımak `app`/`worker` Docker imajlarını 1.55GB'den **516MB**'a, açılış
süresini 1-2 dakikadan **~6 saniyeye** indirdi. Test paketi (837 test) **~33
saniyede** koşuyor — her istekte sessizce gerçek (2 saniye timeout'lu) bir
veritabanı bağlantısı deneyen bir test fixture'ı bulunup düzeltilmeden önce
~400sn'di.

---

### Haber Kaynakları (17)

**Türkçe (11):** TRT Haber, BBC Türkçe, Hürriyet, Hürriyet Spor, Sabah, CNN Türk, Sözcü, Habertürk, HT Spor, Anadolu Ajansı, AA Ekonomi
**İngilizce (6):** BBC Technology, BBC Sport, Guardian Tech, TechCrunch, Hacker News, The Verge

Yeni bir kaynak birkaç satırda eklenebilir — bkz. [Kaynak Ekleme](#kaynak-ekleme).

---

### Frontend (Next.js)

Streamlit panel, ayırt edici bir **sinematik tema sistemi** olan **Next.js 14 + React** arayüzüyle değiştirildi:

- **9 sinematik tema** — Matrix, Godfather, Blade Runner, Dune, Star Wars, Spider-Man, Batman, Wolfenstein + sade **Day** modu. Her tema; renk, font, tam ekran animasyonlu **Canvas arka plan** (dijital yağmur, film greni, neon yağmur, kum fırtınası, yıldız alanı, örümcek ağı, bat-signal, közler) ve geçişte bir flash efekti getirir. **Saf CSS + Canvas — görsel/video asset yok.**
- **Tema registry** (`lib/theme/registry.ts`): tek doğruluk noktası. Yeni tema = 1 kayıt + 1 CSS bloğu + 1 Canvas efekti, tüketici kodu değişmez (Open/Closed). Tüm efektler tek `requestAnimationFrame` döngüsünü paylaşır (`useCanvasScene`).
- **Tam TR / EN i18n**: tüm metinler `lib/i18n.ts`'te; landing, dashboard, hesap ve admin sayfaları birlikte dil değiştirir.
- **Kurulabilir PWA** (manifest + service worker) ve düşük/yüksek **performans profilleri** (canvas efekt yoğunluğu).
- `prefers-reduced-motion`'a saygı gösterir; sekme gizliyken animasyonları duraklatır.

---

### API Endpoint'leri (seçili)

| Metod | Endpoint | Açıklama |
|-------|----------|----------|
| GET | `/api/v1/news` | Haber listesi — cursor pagination, `X-RateLimit-*` header'ları, tier-gated |
| POST | `/api/v1/news/search` | Hibrit anlamsal + anahtar kelime arama, tier bazlı sonuç tavanı (Free 10 / Pro 50 / Enterprise 200) |
| GET | `/api/v1/news/trending` | Trend olan varlıklar (son N saat) |
| GET | `/api/v1/news/{id}/related` | Varlık örtüşmesiyle ilişkili haberler (Pro+) |
| GET | `/api/v1/news/{id}/sources` | Story cluster — bu haberi kim nasıl anlatıyor (ücretsiz) |
| POST | `/api/v1/news/ask` | Kanıta dayalı RAG soru-cevap, genel veya habere özel |
| GET | `/api/v1/news/export` | Ham veri export, CSV veya JSON (sadece Enterprise) |
| GET | `/api/v1/news/sources` | Kayıtlı kaynaklar |
| POST | `/auth/register` · `/auth/login` · `/auth/logout` | Session tabanlı auth (HttpOnly cookie) |
| POST | `/auth/resend-verification` · `/auth/verify-email` | E-posta doğrulama akışı |
| POST | `/auth/forgot-password` · `/auth/reset-password` | Şifre sıfırlama |
| GET/POST/DELETE | `/account/api-key` | Kişisel `X-User-Key` API anahtarı yönetimi |
| GET/POST/PATCH/DELETE | `/subscriptions` | Bülten / keyword-alert tercihleri |
| POST | `/billing/checkout` · `/billing/portal` | Stripe Checkout & billing portal |
| GET | `/admin/users` · `/admin/usage` · `/admin/sponsors` | Admin analytics, kullanıcı/rol & sponsor yönetimi |
| GET | `/feed.xml` | RSS/Atom feed |
| WS | `/ws/feed` | Gerçek zamanlı haber akışı (Pro+, kullanıcı başına + toplam bağlantı tavanı) |
| POST | `/news/scrape` · `/news/reindex` · `/news/reanalyze` | Bakım işlemleri (`X-API-Key`) |
| GET | `/health` · `/metrics` | Sağlık durumu (DB/Redpanda/ChromaDB) · Prometheus metrikleri |
| GET | `/docs` | Swagger UI |

**Tam interaktif referans:** [nexstreamnewsengine.duckdns.org/api/docs](https://nexstreamnewsengine.duckdns.org/api/docs) — her endpoint, istek/cevap şeması, "Try it out" butonuyla doğrudan test. Yukarıdaki endpoint'leri örnek isteklerle kapsayan, doğrudan içe aktarılabilir bir [Postman koleksiyonu](docs/NexStream.postman_collection.json) da var.

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

#### Servisler

| Servis | URL | Açıklama |
|--------|-----|----------|
| Frontend | http://localhost:3000 | Next.js arayüzü |
| API | http://localhost:8000 | FastAPI REST |
| API Docs | http://localhost:8000/docs | Swagger UI |
| DB Admin | http://localhost:8080 | Adminer |

Konteynerler ayağa kalktıktan sonra `http://localhost:3000` arayüzünü aç. Scheduler her 10 dakikada bir scrape'i otomatik tetikler, Kafka-uyumlu worker haberleri AI analizinden geçirir — manuel işlem gerekmez. `http://localhost:8000/health` ile DB / Kafka / ChromaDB / embedder servisinin yeşil olduğunu doğrula. Embedding modeli build anında `embedder` image'ına gömülü olduğu için ilk çalıştırmada indirme YOK — `app` ve `worker` sadece modelin diskten yüklenmesini bekler (~30-60sn).

> **Temiz aç/kapa:** `docker compose down` ardından `docker compose up -d`. Redpanda ve ChromaDB `restart: unless-stopped` ile çalışır; ani kapanışta bile yığın kendini toparlar.

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

**837 test** — domain, application ve adapter katmanları. Her dış çağrı (Groq, Kafka, DB, ChromaDB, SMTP/Resend) mock'lanır; ağ erişimi gerekmez, gerçek e-posta gönderilmez.

<details>
<summary>Gerçek lokal çalıştırma çıktısı</summary>

```
$ python -m pytest tests/ -q
........................................................................ [  8%]
........................................................................ [ 17%]
........................................................................ [ 25%]
........................................................................ [ 34%]
........................................................................ [ 43%]
........................................................................ [ 51%]
........................................................................ [ 60%]
........................................................................ [ 68%]
........................................................................ [ 77%]
........................................................................ [ 86%]
........................................................................ [ 94%]
.............................................                            [100%]
837 passed, 1 warning in 32.76s
```

</details>

---

### Kaynak Ekleme

`BaseRssScraper` deseni ve source registry sayesinde yeni bir kaynak eklemek birkaç satır tutar:

```python
# src/adapters/scrapers/rss_scrapers.py
class MyNewsScraper(BaseRssScraper):
    def __init__(self):
        self.url = "https://example.com/rss"
        self.source_name = "My News"
        self.limit = 25
```

Sonra `src/adapters/scrapers/registry.py`'de kaydet:

```python
SCRAPER_REGISTRY = {
    ...
    "My News": MyNewsScraper(),
}
```

---

### Yeni AI Analyzer Ekleme

`AnalysisPort` arayüzünü implemente edip `adapters/analysis/factory.py` üzerinden bağla — iş mantığında hiçbir değişiklik gerekmez:

```python
# src/adapters/analysis/my_analyzer.py
class MyAnalyzer(AnalysisPort):
    def analyze_text(self, text: str) -> dict:
        return {"sentiment_score": 0.8, "sentiment_label": "Positive", "summary": "..."}
```

Varsayılan `FallbackAnalyzer`, Groq → Hugging Face → nötr fallback zincirini uygular; tek bir sağlayıcının çökmesi worker'ı asla düşürmez.

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
| `BILLING_DEV_MODE` | Stripe'sız anında tier yükseltme (sadece lokal demo — prod'da ASLA) |
| `ADMIN_EMAILS` | Virgülle ayrılmış liste, DB yazmadan admin bootstrap eder |
| `ENVIRONMENT` | `production` iken güvensiz config (varsayılan API key, `CORS_ORIGINS=*`, dev billing, güvensiz cookie) ile açılmayı reddeder |
| `EXPORT_MAX_ROWS` | Ham veri export üst satır sınırı (varsayılan 20000) |
| `WS_MAX_CONNECTIONS_PER_USER` / `WS_MAX_TOTAL_CONNECTIONS` | `/ws/feed` kullanıcı başına / toplam bağlantı tavanı |
| `RAG_RETRIEVAL_THRESHOLD` | `/news/ask`'in LLM'e gitmeden önce gerektirdiği minimum retrieval güveni (varsayılan 0.4) |
| `VAPID_PUBLIC_KEY` / `VAPID_PRIVATE_KEY` | Web push bildirimleri (boşsa devre dışı) |
| `SENTRY_DSN` | Backend hata takibi, `app`+`worker` (boşsa no-op) |
| `NEXT_PUBLIC_POSTHOG_KEY` | Frontend ürün analytics (boşsa no-op) |
| `BACKUP_GPG_PASSPHRASE` / `RCLONE_REMOTE` | Yedek şifreleme (GPG) / offsite upload — ikisi de opt-in |

---

### API Katmanları

| Tier | Fiyat | Günlük API kotası | Arama sonucu tavanı | Öne çıkanlar |
|------|-------|--------------------|-----------------------|--------------|
| Free | $0 | 100 istek | 10 sonuç | Haber & anlamsal arama, günlük digest |
| Pro | $9.99 / ay | 2.000 istek | 50 sonuç | WebSocket canlı akış, keyword alert, ilişki grafı |
| Enterprise | $49.99 / ay | Sınırsız | 200 sonuç | Ham veri export (CSV/JSON), özel kaynaklar, SLA, öncelikli destek |

> Yukarıdakilerin hepsi **gerçekten sunucu tarafında zorunlu** — sadece pazarlama metni değil: bkz. `TIER_SEARCH_RESULT_CAP` ve `/ws/feed`, `/news/{id}/related`, `/news/export` üzerindeki `tier_at_least()` kontrolleri. Ödeme Stripe yapılandırması gerektirir; yoksa yükseltme endpoint'leri bilinçli olarak `503` döner (ya da lokal Stripe'sız demo için `BILLING_DEV_MODE=true`). Admin endpoint'leri paylaşımlı `API_KEY` veya admin/moderator kullanıcı oturumunu kabul eder.

---

### CI/CD

`main`'e her push / PR, GitHub Actions'ı tetikler:

1. Bir PostgreSQL 15 servis konteyneri ayağa kaldırır
2. Python bağımlılıklarını kurar (`pytest-asyncio` dahil)
3. `pytest` ile 837 testin tamamını çalıştırır
4. Başarılı/başarısız durumunu raporlar
5. **Sadece `main`'de, testler geçerse:** AWS SSM üzerinden production'a bağlanır, kodu çeker ve yeniden build eder, ardından yeni sürümün gerçekten ayakta olduğunu `/api/health` ile doğrular — `main`'e bir merge elle hiçbir adım gerektirmeden production'a ulaşır

Dependabot da pip, npm ve GitHub Actions bağımlılıkları için haftalık PR açar (review/merge/rebuild kararı bilinçli olarak kullanıcıda kalır — otomatik merge yok).

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
| v1.11 | Billing dev mode, rol tabanlı admin, self-service kullanım paneli, kişisel API anahtarları, proje geneli clean-code | ✅ |
| v1.12 | Responsive UI, WCAG AA erişilebilirlik, SEO, tema performans profilleri | ✅ |
| v1.13 | Rol hiyerarşisi (user / moderator / admin) | ✅ |
| v1.14 | Tier-gating sunucu tarafında gerçekten kilitli (arama tavanı, ilişki grafı, canlı akış) | ✅ |
| v1.15 | E-posta doğrulama akışı | ✅ |
| v1.16 | Ham veri export (Enterprise), canlı dashboard liste enjeksiyonu | ✅ |
| v1.17 | Kapsamlı güvenlik denetimi & sertleştirme (auth, injection, secrets, DoS, bağımlılıklar) | ✅ |
| v1.18 | Kafka→Redpanda geçişi (ARM-uyumlu), kurulabilir PWA, Dependabot, şifreli/offsite yedek, WebSocket bağlantı tavanı | ✅ |
| v1.19 | Public arama endpoint'indeki son bilinen rate-limit boşluğu kapatıldı | ✅ |
| v2.0 | Public launch: RAM optimizasyonlu deploy, ücretsiz katman bulut VPS + gerçek domain + TLS | ✅ |
| v2.1 | Owner rolü, kademeli rol yönetimi, gerçek e-posta gönderimi (SMTP) | ✅ |
| v2.1.1 | Canlı güvenlik incelemesi: Groq model değişimi, WebSocket düzeltmesi, nginx header düzeltmesi, Türkçe arama skoru düzeltmesi, `main` senkronizasyonu | ✅ |
| v2.2–v2.3 | Arama sorgu genişletme (Groq ile ilişkili terimler), kaydet/sonra oku, corroboration rozeti, tarayıcı-yerel TTS, story cluster, moderatör kullanıcı banlama, sıralanabilir admin tabloları | ✅ |
| v2.4 | Hata takibi + ürün analytics: Sentry (backend) ve PostHog (frontend), ikisi de tamamen opsiyonel | ✅ |
| v2.5 | Web push bildirimleri — mevcut keyword-alert eşleşmesinin ikinci teslimat kanalı | ✅ |
| v2.6 | Kanıta dayalı RAG soru-cevap (`/api/v1/news/ask`) — deterministik kanıt kapısı, soru başına en fazla 1 Groq çağrısı | ✅ |
| Sıradaki | Daha zengin Q&A kanıtı için tam makale metnini talep üzerine çekmek, bir güven/alaka skorlaması turu, anasayfa tasarım yenilemesi | 🔜 Planlanan |

*Gerçek Stripe billing bilinçli olarak ertelenmiş durumda — kod tarafı hazır ama şu anki gelir yönü reklam destekli ücretsiz katman. Bu tablo mühendislik kararlarını takip ediyor; bu türden ürün/iş kararları dahili olarak izleniyor.*

---

### Lisans

MIT Lisansı — detaylar için [LICENSE](LICENSE).

---

<div align="center">

**NexStream** · Python · FastAPI · Redpanda · Groq · ChromaDB · Next.js

</div>
