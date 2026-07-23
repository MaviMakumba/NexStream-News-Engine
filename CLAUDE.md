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
│   ├── schemas/
│   │   └── news_schema.py         # Pydantic: NewsResponse, SearchRequest, SearchResult, TrendingResponse, RelatedResponse
│   └── scoring/                   # Saf domain skorlama (v1.8) — dış bağımlılık yok
│       ├── quality.py             # compute_quality_score — uzunluk/entity/summary/başlık
│       └── credibility.py         # SOURCE_CREDIBILITY seed + compute_credibility
├── application/
│   └── services/news_service.py   # Orchestration — port'ları bağlar, get_related, _enrich_metadata dahil
├── adapters/
│   ├── analysis/
│   │   ├── groq_analyzer.py       # Groq llama-3.1-8b-instant — birincil analyzer (v1.5+)
│   │   ├── huggingface_analyzer.py # HF Inference API — opsiyonel yedek (v1.8)
│   │   ├── fallback_analyzer.py   # Groq dene, başarısızsa HF, hepsi olmazsa nötr (v1.8)
│   │   ├── common.py              # Paylaşılan prompt + JSON parse + nötr fallback (v1.8)
│   │   └── factory.py             # build_analyzer() — kompozisyon noktası (v1.8)
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
│   │   ├── scheduler_service.py   # 10dk'da bir Kafka'ya mesaj atar
│   │   ├── newsletter_job.py      # günlük digest (05:00 UTC)
│   │   └── retention_job.py       # günlük ChromaDB/Postgres temizlik (04:00 UTC, v1.11 sonrası)
│   ├── search/
│   │   ├── sentence_transformer_embedder.py  # SentenceTransformerEmbedder (singleton)
│   │   └── chroma_search_repository.py       # ChromaDB adapter — index + search + dedup (v1.5+)
│   └── api/
│       ├── auth.py               # verify_api_key() — paylaşımlı X-API-Key (makine-makine)
│       ├── auth_utils.py         # get_optional_user/get_current_user/require_admin/check_tier_limit (v1.9-v1.11)
│       ├── limiter.py            # slowapi Limiter singleton (v1.3+)
│       ├── metrics.py            # Prometheus custom metrics (v1.6+)
│       └── routers/
│           ├── news_router.py    # GET /news, /trending, /{id}/related, POST /scrape, /search, /reindex, /sources
│           ├── health_router.py  # GET /health — DB + Kafka + ChromaDB durumu
│           ├── auth_router.py    # /auth: register, login, logout, me (v1.9)
│           ├── account_router.py # /account: usage paneli + kişisel API key (v1.11)
│           ├── admin_router.py   # /admin: usage + sponsor CRUD — require_admin (v1.11)
│           ├── billing_router.py # /billing: Stripe + dev-mode bypass + /config (v1.11)
│           ├── subscription_router.py # /subscriptions: newsletter abonelikleri (v1.7)
│           ├── feed_router.py    # /feed.xml RSS 2.0 (v1.7)
│           ├── websocket_router.py # /ws/feed canlı akış (v1.7)
│           └── v1/news_router_v1.py # /api/v1: sürümlü, kotalı public API (v1.7+)
├── infrastructure/
│   ├── config/
│   │   ├── database.py           # SQLAlchemy engine — settings üzerinden bağlantı
│   │   └── settings.py           # Pydantic Settings — tek merkezi config (v1.3+)
│   └── logging/
│       └── logger.py             # setup_logging(), JSON/text formatter (v1.3+)
├── dependencies.py                # FastAPI DI — GroqAnalyzer, NewsRepository, ChromaSearch inject
└── main.py                        # FastAPI app
migrations/
├── v1_5_add_entities_topic.sql    # v1.5 DB migration (entities, topic, is_duplicate)
├── v1_7_subscriptions.sql         # v1.7 DB migration (subscribers tablosu)
├── v1_8_quality_credibility.sql   # v1.8 DB migration (quality_score, credibility_score, corroboration_count)
├── v1_9_users_sessions_usage_sponsor.sql  # v1.9 (users, user_sessions, usage_logs, sponsors)
├── v1_11_admin_api_keys.sql       # v1.11 (users.is_admin, users.api_key + unique index)
└── v1_12_password_reset_tokens.sql # şifre sıfırlama (password_reset_tokens tablosu)
frontend/                          # Next.js 14 + React (Streamlit'in yerini aldı, v1.10)
├── app/                           # App Router sayfaları (landing, dashboard, search, account, admin, auth)
│   ├── layout.tsx                 # data-theme=<id> + Google Fonts linkleri
│   └── globals.css                # 9 tema token bloğu + component class'ları + geçiş flash'ı
├── components/                    # Navbar, NewsCard, TrendingPills, SentimentBadge, TierBadge
├── lib/
│   ├── i18n.ts                    # UI sözlüğü + FEATURES/PRICING/TIER_DETAILS (tam TR/EN)
│   ├── settings-context.tsx       # tema+dil context, data-theme uygular, ThemeBackground render
│   └── theme/                     # SİNEMATİK TEMA SİSTEMİ (SOLID)
│       ├── types.ts               # ThemeId, ThemeDefinition
│       ├── registry.ts            # THEMES tek doğruluk kaynağı — yeni tema = 1 kayıt + 1 CSS + 1 efekt
│       ├── useCanvasScene.ts      # paylaşılan RAF döngüsü (DPR, reduced-motion, tab gizli=duraklat)
│       ├── ThemeBackground.tsx    # aktif temanın efektini key'li render eder
│       └── effects/               # 8 canvas efekti: MatrixRain, FilmGrain, NeonRain, SandStorm,
│                                  #   Starfield, WebStrands, BatSignal, EmberHaze (+ shared.ts)
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
| redpanda | — (internal) | Mesaj kuyruğu (Kafka-uyumlu, tek binary — v1.18'de Kafka+Zookeeper'ın yerine geçti) |
| worker | — | Kafka-uyumlu consumer + Groq analyzer |
| scheduler | — | 10dk'da bir scrape tetikler |
| frontend | 3000 | Next.js dashboard |
| chromadb | — (internal) | Vektör DB |
| redis | — (internal) | Cache (opsiyonel, boşsa NullCache) |

### docker-compose.prod.yml (production)

| Servis | Port | Açıklama |
|--------|------|----------|
| nginx | 80, 443 | Reverse proxy + TLS termination |
| certbot | — | Let's Encrypt otomatik yenileme |
| app | — (internal) | FastAPI + /metrics endpoint |
| db | — (internal) | PostgreSQL 15 |
| redpanda | — (internal) | Mesaj kuyruğu (Kafka-uyumlu, tek binary — v1.18'de Kafka+Zookeeper'ın yerine geçti) |
| worker | — (internal) | Kafka-uyumlu consumer + Groq analyzer |
| scheduler | — (internal) | 10dk'da bir scrape tetikler |
| frontend | — (internal) | Next.js (nginx üzerinden) |
| chromadb | — (internal) | Vektör DB |
| redis | — (internal) | Cache (opsiyonel, boşsa NullCache) |
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

- **Versiyon:** v1.19.0 ✅ public `/news/search` kota atlatma kapatıldı (kod tarafı v1.18 deploy hazırlığı ile birlikte tamamlandı; canlıya çıkış Oracle kayıt sorunuyla BLOKE — bkz. "SIRADAKİ GÖREVLER" v1.18/v1.19 blokları ve v2.0 madde 1). Önceki büyük dönüm noktası: v1.11.0 Monetizasyon & Erişim (billing dev-mode, rol tabanlı admin, self-service kullanım paneli, kullanıcı başına API key) + proje geneli clean-code refactoring — v1.12 → v1.19 arası TÜM işler "SIRADAKİ GÖREVLER" bölümünde madde madde kayıtlı.
- **v1.11 sonrası ekler (v1.12 öncesi ara işler — tarihsel):**
  1. **Şifremi unuttum / şifre sıfırlama** — `POST /auth/forgot-password` + `POST /auth/reset-password`, `password_reset_tokens` tablosu (`migrations/v1_12_password_reset_tokens.sql`), `EmailPort.send_password_reset` (Console + Resend), şifre değişince tüm oturumlar düşürülür.
  2. **Prod deploy tutarlılık düzeltmesi** — `docker-compose.prod.yml`'den silinmiş Streamlit `dashboard` servisi kaldırıldı, yerine `frontend` (Next.js, `frontend/Dockerfile` standalone build) eklendi; `redis` servisi prod'a eklendi; nginx `dashboard:8501` yerine `frontend:3000`'e yönlendiriyor; CI'a frontend `npm run build` job'u eklendi.
  3. **KRİTİK bug fix — ChromaDB indeksleme:** `NewsRepository.save_article()` artık `commit()` sonrası `article.id`'yi domain nesnesine geri yazıyor (`self.db.refresh(orm_obj); article.id = orm_obj.id`). Önceden bu satır yoktu → `NewsService.update_news_from_source`'daki `if self.search_repository and article.id:` şartı normal scrape akışında HİÇBİR ZAMAN sağlanmıyordu, yani hiçbir yeni haber ChromaDB'ye indexlenmiyordu (sadece `reindex_all`/`reanalyze_missed` gibi haberi DB'den taze çeken yollar indexliyordu). Tespit: Postgres'te 2293 haber varken ChromaDB'de sadece 825'i aranabilirdi. `POST /news/reindex` ile backfill yapıldı.
  4. **Arama sıralaması — recency decay** — `hybrid_search` skoru artık `relevance * decay_factor` (çarpımsal, additive bonus'un yerine geçti). `decay_factor`: bugün → 1.0, `search_recency_window_days` (30) sonra → `search_recency_decay_floor` (0.5) tabanına lineer iner. ChromaDB metadata'sına `published_at` eklendi (`published_at or created_at` fallback), `SearchResult` şemasına `created_at` eklendi. Eşit skorlu sonuçlarda ikincil sıralama anahtarı da `_recency_factor`.
  5. **Retention job** (`src/adapters/scheduling/retention_job.py`, her gün 04:00 UTC) — iki katman: ChromaDB'den `chroma_retention_days` (90, varsayılan AÇIK) gününden eski vektörleri kaldırır (Postgres etkilenmez, `reindex_all` ile geri gelir); Postgres'ten `db_retention_days` (0, varsayılan KAPALI) kalıcı silme, bilinçli opt-in. Ayrıca son 7 günün haberlerini her çalıştığında yeniden indexleyerek indeksleme boşluklarına karşı kendini onarır (self-healing).
  6. **Cookie tabanlı session auth** — `/auth/register`+`/auth/login` artık body'de token DÖNMÜYOR; HttpOnly `nxs_session` cookie'si set ediyor (SameSite=Lax, `secure=settings.session_cookie_secure`). `get_optional_user` sırasıyla `X-Session-Token` header → `nxs_session` cookie → `X-User-Key` header dener. Amaç: SSR'ın bilemediği client-only token hydration'ından doğan "önce misafir, sonra giriş yapılmış" FOUC'unu bitirmek. Frontend `lib/api.ts` tüm fetch'lerde `credentials: "include"` kullanır; `AuthCtx` artık `token` alanı taşımaz, sadece `user`.
- **Test sayısı:** 522 test, hepsi yeşil (backend); frontend `tsc --noEmit` temiz
- **Frontend:** Next.js 14 + React. Streamlit dashboard tamamen kaldırıldı (`dashboard/app.py` silindi, compose'dan çıktı). 9 sinematik tema, tam TR/EN i18n, PWA (manifest + service worker, v1.18). Port **3000**.
- **Mesaj kuyruğu:** Redpanda (v1.18'de Kafka+Zookeeper'ın yerine geçti — tek binary, ARM uyumlu, `aiokafka` client kodu değişmedi, sadece wire-protokolü konuşuyor).
- **Haber kaynağı:** 17 (11 → 17, +Anadolu Ajansı, AA Ekonomi, Guardian Tech, TechCrunch, Hacker News, The Verge)
- **CI/CD:** GitHub Actions — push/PR on main, postgres:15 service, `python -m pytest` + Dependabot (pip+npm+github-actions, haftalık, v1.18)
- **Branch:** main (tüm özellikler merge edildi)
- **Hedef:** CV/portfolio projesi → canlı ürüne geçiş (ücretsiz başla, gelir varsa harca)
- **Kısıt:** VPS'te 7/24 bağımsız çalışacak, local bağımlılık yok. **Bütçe: GERÇEKTEN $0/ay** (kalıcı kısıt, 22 Temmuz 2026'da netleşti — Hetzner CX22 bile fazla) → deploy hedefi Oracle Cloud Always Free ARM + DuckDNS (bkz. v2.0 madde 1), şu an Oracle kart doğrulama sorunuyla BLOKE.
- **Lokal araçlar:** Node.js v24 + npm host'a kuruldu (winget). Docker Desktop, PostgreSQL 17, Git zaten kurulu.

---

## TAMAMLANAN ÖZELLİKLER (v1.2.0)

### Hybrid Search
- `POST /news/search`: ChromaDB (semantic) + PostgreSQL (keyword) birleşik
- Coverage-based skor, normalize embedding, `1/(1+distance)` formülü
- **v1.11 sonrası:** nihai skor `relevance * recency_decay` (çarpımsal) —
  `NewsService.hybrid_search`/`_decay_factor`'a bak, detay MEVCUT DURUM'da

### Haber Kaynakları (17 kaynak, v1.8)
- TR: TRT Haber, BBC Türkçe, Hürriyet, Hürriyet Spor, Sabah, CNN Türk, Sözcü, Habertürk, HT Spor, Anadolu Ajansı, AA Ekonomi
- EN: BBC Technology, BBC Sport, Guardian Tech, TechCrunch, Hacker News, The Verge
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
3. **Network isolation** — docker-compose.yml: db/redpanda/chromadb port'ları kapatıldı
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

### v1.8.0 — AI & Veri Kalitesi ✅ TAMAMLANDI
1. **Kaynak genişletme** — 11 → 17 kaynak: Anadolu Ajansı, AA Ekonomi (TR), Guardian Tech, TechCrunch, Hacker News, The Verge (EN). `BaseRssScraper` pattern, registry + `settings.scrape_sources` güncellendi. (Reuters/Ekonomist atlandı: güvenilir public RSS yok)
2. **Haber ilişki grafı** — `GET /news/{id}/related` (news + v1 router), entity overlap ile ilgili haberler. On-the-fly hesap (ayrı tablo YOK): `repository.get_article_by_id` + `get_articles_with_entities`, `service.get_related` overlap'e göre sıralar, ortak entity'ler orijinal yazımıyla döner
3. **Kaynak güvenilirlik skorlaması** — `credibility_score` + `corroboration_count` kolonları. Taban skor `domain/scoring/credibility.py` seed dict; corroboration = aynı olayı (>=2 ortak entity) raporlayan FARKLI kaynak sayısı, ingest'te `_enrich_metadata` ile hesaplanır
4. **İçerik kalite skorlama** — `quality_score` kolonu, deterministik `domain/scoring/quality.py` (uzunluk + entity yoğunluğu + summary + başlık). v1 API `min_quality` filtresi. Reanalyze yolları da quality hesaplar
5. **Cloud LLM fallback** — `AnalysisError` + `analyze_or_raise` port'a eklendi. `GroqAnalyzer` (birincil) + `HuggingFaceAnalyzer` (opsiyonel yedek, `HUGGINGFACE_API_KEY` boşsa devre dışı) → `FallbackAnalyzer` zinciri. Ortak prompt/parse `adapters/analysis/common.py`. `factory.build_analyzer()` dependencies + kafka_consumer'da kullanılır
6. **DB migration** — `migrations/v1_8_quality_credibility.sql` (quality_score, credibility_score, corroboration_count + index)

Sonuç: 217 → 280 test (+63)

### v1.11.0 — Monetizasyon & Erişim Tamamlama ✅ TAMAMLANDI
1. **Billing dev-mode** — `BILLING_DEV_MODE=true` iken `/billing/checkout` Stripe'a gitmeden tier'ı anında günceller (`dev_mode: true` döner); `/billing/dev/downgrade` Free'ye çeker (flag kapalıyken 404). `GET /billing/config` public — frontend ödeme akışını buna göre seçer. Gerçek Stripe yolu aynen korunur (anahtar girilince çalışır).
2. **Rol tabanlı admin** — `users.is_admin` kolonu + `migrations/v1_11_admin_api_keys.sql`. `require_admin` dependency: geçerli `X-API-Key` (makine) VEYA admin kullanıcı oturumu (`is_admin=true` ya da e-posta `ADMIN_EMAILS` listesinde — env ile bootstrap, DB yazmadan). Yetkisiz kullanıcı 403, anonim 401. Frontend admin sayfaları admin oturumuyla anahtar istemeden açılır; admin olmayana eski API key girişi kalır. Navbar/hesap sayfası admin linkleri sadece admin'e görünür.
3. **Self-service kullanım paneli** — `GET /account/usage`: tier, günlük limit, bugünkü kullanım, kalan kota, endpoint bazlı istatistik. Hesap sayfasında KPI kartları + kota progress bar (%90 üzeri kırmızı).
4. **Kullanıcı başına API key** — `users.api_key` kolonu (unique index). `POST /account/api-key` üret/rotate (`nxs_` önekli), `DELETE` iptal, `GET` görüntüle. `/api/v1` istekleri `X-User-Key` header'ı ile session'sız kullanılabilir; kota kullanıcının tier'ından uygulanır, usage middleware her iki kimliği de çözer.
5. **Clean-code refactoring** — TÜM src/ modüllerinde docstring (%100 kapsam), `auth_router`+`auth_utils` oturum çözme mantığı `resolve_session_user`'da birleşti, `NewsService._apply_analysis` ile 3 yerdeki tekrar giderildi, ölü `adapters/api/controller.py` silindi, inline import'lar üste taşındı, frontend yeni dosyalarına açıklama katmanı.

Sonuç: 343 → 373 test (+30: account router 9, billing dev-mode 8, admin rol/user-key 13)

---

## SIRADAKİ GÖREVLER (Yol Haritası — v1.12 → v2.0)

Eski detay plan: `C:\Users\eren8\.claude\plans\ancient-watching-crescent.md`
Sonraki oturumu başlatmak için: **"Yol haritasına devam — CLAUDE.md'deki sıradaki sürümü uygula."**

**Tamamlananlar:** v1.2 → v1.11 (detaylar yukarıdaki milestone'larda) + v1.11 sonrası 6 ara iş (şifre sıfırlama, prod deploy tutarlılığı, kritik ChromaDB indeksleme bug fix, arama recency sıralaması, retention job, cookie tabanlı session auth — detay MEVCUT DURUM'da) + go-live hazırlığı + admin paneli/rol hiyerarşisi + sponsor/email/digest düzeltmeleri (8 Temmuz 2026) + v1.12 (responsive/erişilebilirlik/SEO/tema perf, TAMAMLANDI) + WebSocket canlı ticker + v1.14 tier-gating gerçek yapıldı + canlı testte bulunan auth bug'ları (20 Temmuz 2026) + v1.15 e-posta doğrulama akışı + v1.16 ham veri export + dashboard canlı liste enjeksiyonu + v1.17 kapsamlı güvenlik denetimi & sertleştirme (21 Temmuz 2026) + v1.18 Kafka→Redpanda + PWA + ücretsiz deploy hazırlığı + Dependabot + `/ws/feed` bağlantı limiti + yedek şifreleme/offsite (22 Temmuz 2026) + **v1.19 public `/news/search` kota atlatma kapatıldı** (23 Temmuz 2026, detay aşağıda). 522 backend test, lokalde TAM çalışır (billing dahil — `BILLING_DEV_MODE=true` ile Stripe'sız demo). Gerçek Stripe entegrasyonu kod tarafında hazır; sadece gerçek hesap + `STRIPE_*` anahtarları + `stripe listen` webhook'u gerekir (v2.0 deploy işi). **Sıradaki oturum:** v2.0 domain/VPS deploy — kod tarafındaki TÜM v2.0 maddeleri hazır (Oracle Cloud Free ARM + DuckDNS'e göre yeniden yazıldı, bkz. v2.0 madde 1). **BLOKE:** Oracle hesap açılışı kart doğrulamasında "Transaction Failed" veriyor (23 Temmuz 2026 itibarıyla çözülmedi) — bir sonraki oturum önce bu denemenin sonucunu sormalı; başarılıysa `DEPLOY.md` adım adım takip edilir, hâlâ başarısızsa Google Cloud e2-micro alternatifi değerlendirilmeli. Deploy öncesi MUTLAKA yapılacaklar (v1.17 denetiminden): `.env`'de `ENVIRONMENT=production` + gerçek `CORS_ORIGINS` + güçlü `GRAFANA_PASSWORD` set edilmeli (yoksa uygulama/compose zaten sert hata verip durur — bilinçli tasarım). Kalan bilinçli-kapatılmayan güvenlik maddeleri: token'ların DB'de düz metin olması (belgelenmiş sadelik tercihi), `/docs`'un prod'da açık kalması (API dok portalı özelliğiyle çelişmesin diye bilinçli).

### v1.12 — UX, Erişilebilirlik & SEO Cilası (frontend ağırlıklı) — ✅ TAMAMLANDI (20 Temmuz 2026)
1. ✅ **Responsive geçiş** — Navbar mobil menüsü (8 Temmuz) + dashboard/search/account/admin sayfalarının responsive taraması (20 Temmuz, detay aşağıda).
2. ✅ **Erişilebilirlik** — kontrast (9 tema), focus/aria/klavye (20 Temmuz, detay aşağıda). Bkz. mevcut global `:focus-visible` kuralı (`globals.css`) zaten iyiydi, sadece kontrast + aria/klavye eksikti.
3. ✅ **SEO** — go-live hazırlık turunda yapıldı (8 Temmuz, bkz. aşağıdaki blok): generateMetadata, robots.ts, sitemap.ts.
4. ✅ **Tema ince ayarı** — efekt yoğunluğu/performans profilleri (low/high) eklendi (20 Temmuz, detay aşağıda). Yeni tema eklenmedi (kapsam dışı bırakıldı, istenirse ayrı iş).
5. ✅ **Durum cilası** — auth loading state tutarlılığı (20 Temmuz). Search/admin sayfalarında zaten makul error/empty state'ler vardı, dashboard'daki skeleton deseni korundu.

### v2.0 — Public Launch (v1.12 sonrası)
1. ~~**Domain & VPS — Hetzner CX22**~~ — ❌ **22 Temmuz 2026'da PLAN DEĞİŞTİ:** kullanıcının bütçesi GERÇEKTEN $0/ay (kalıcı kısıt, Hetzner'in ~€4.5/ay'ı bile fazla). Yeni plan: **Oracle Cloud "Always Free" ARM** (VM.Standard.A1.Flex, 4 vCPU/24GB, aarch64) + **DuckDNS ücretsiz subdomain** (`nexstream.duckdns.org`, satın alınmış domain YOK) + `docker-compose.prod.yml` ile deploy. Cloudflare CDN/UptimeRobot hâlâ geçerli (ücretsiz). Detay + Oracle'a özgü tuzaklar (VCN Security List, kapasite hataları) `DEPLOY.md`'de. **BLOKE (23 Temmuz 2026 itibarıyla):** Oracle hesap açılışında kart doğrulaması "Transaction Failed" veriyor — TR bankalarının çoğu Oracle'ın yurt dışı doğrulama çekimini varsayılan engelliyor. Troubleshooting sırası: (1) bankayı arayıp yurt dışı/online işlem izni aç, (2) kredi kartı dene (debit/prepaid değil), (3) VPN kapalı olsun, (4) fatura adresi banka kaydıyla birebir aynı olsun, (5) art arda deneme, birkaç saat/gün bekle, (6) farklı kart dene. Başarısız olursa alternatif: Google Cloud e2-micro Free Tier (çok daha kısıtlı — 1 vCPU/1GB x86, mimari ciddi sadeleştirilmeli).
2. **API dökümantasyon portalı** — Swagger/Redoc cila, demo API key, kullanım örnekleri, Postman collection.
3. **Launch içeriği** — landing son metinler, OG görselleri, Product Hunt materyali.
4. **README** — ✅ v1.10'da tüm proje geneli güncellendi (gerekirse Mermaid diyagram + GIF demo eklenir).
5. **Gerçek Stripe entegrasyonu** — kod tarafı hazır (bkz. "Kritik Kararlar" ve BİLİNEN NOTLAR'daki billing maddeleri); sadece gerçek hesap + `STRIPE_*` anahtarları + `stripe listen` webhook'u + `BILLING_DEV_MODE=false` gerekir. Kullanıcı dev modda tek tıkla tier değiştirmenin "bir şey değiştirmediğini" fark etti — bu KASITLI (dev-mode simülasyon, ödeme yok), gerçek kısıtlama ancak burada devreye girer.
6. ~~**KRİTİK — Tier-gating gerçek değil**~~ — ✅ **20 Temmuz 2026'da tamamlandı** (detay aşağıda): arama sonucu tavanı (Free 10/Pro 50/Enterprise 200), `/api/v1/news/{id}/related` (Pro+), `/ws/feed` (Pro+), `subscription_router.py`'deki `frequency=instant` (Pro+, e-posta→User tier eşlemesiyle) artık gerçekten kilitli. ~~"Ham veri export" hâlâ hiç yazılmamış~~ — ✅ **21 Temmuz 2026'da tamamlandı** (v1.16, detay aşağıda).
7. ~~**Dependabot kurulumu**~~ — ✅ **23 Temmuz 2026'da tamamlandı** (v1.18 commit'inde, `.github/dependabot.yml`): pip (kök dizin — `requirements.txt` + `requirements-light.txt` otomatik taranır), npm (`/frontend`), github-actions ekosistemleri, üçü de haftalık Pazartesi taraması, `dependencies`/`backend`/`frontend`/`ci` etiketleri, `chore(deps)` commit prefix'i. Review/merge/rebuild kararı hâlâ kullanıcıda (bilinçli — otomatik merge/deploy yok). Bağımlılık güncellemesi geldiğinde unutulmaması gereken: Docker image REBUILD edilmeli (`docker-compose up --build -d`), sadece `restart` yetmez — pin'ler image'a build anında gömülür.

**✅ v1.18 — Kafka→Redpanda + PWA + ücretsiz deploy hazırlığı (22 Temmuz 2026, kod tarafı tamamlandı, deploy Oracle kayıt sorunuyla BLOKE):**
- **Neden:** Kullanıcı v2.0 deploy'a başlamak isteyince Hetzner CX22 bile ($0/ay kalıcı bütçe kısıtına göre) fazla bulundu — köklü bir plan değişikliği gerekti (detay yukarıda v2.0 madde 1'de).
- **Kafka+Zookeeper → Redpanda** — Confluent'in Kafka+Zookeeper Docker imajları sadece amd64; gerçekten sonsuza dek ücretsiz güçlü sunucu Oracle Cloud Always Free ARM (aarch64) olduğu için imaj uyumsuzluğu doğdu. Redpanda Kafka wire-protokolünü konuşan tek-binary bir alternatif — `aiokafka` client kodu HİÇ değişmedi, sadece `docker-compose.yml`/`docker-compose.prod.yml`'de `zookeeper`+`kafka` servisleri silinip tek `redpanda` servisi (`docker.redpanda.com/redpandadata/redpanda:v24.2.7`) eklendi, `KAFKA_BOOTSTRAP_SERVERS=redpanda:29092`. `settings.py`'deki `kafka_bootstrap_servers`/`kafka_host` alan adları BİLİNÇLİ korundu (wire-protokolünü tanımlıyorlar, broker yazılımını değil). Değerlendirilip elenen alternatifler: Redis Streams (mevcut Redis'i kullanır ama `XADD`/`XREADGROUP`'a yeniden yazım ister), RabbitMQ (farklı protokol, en büyük yeniden yazım).
- **PWA (frontend, sıfırdan)** — `frontend/public/manifest.webmanifest`, `frontend/public/sw.js` (elle yazılmış minimal service worker, `next-pwa` KULLANILMADI — `/api/` hiçbir zaman cache'lenmiyor, sadece statik ikon/manifest cache-first), `frontend/components/ServiceWorkerRegistration.tsx` (client component, `layout.tsx`'teki bloklayıcı tema-init script'iyle karıştırılmadı). `layout.tsx` metadata+viewport export güncellendi (`themeColor` Next 14'te metadata'dan deprecated, `viewport`'a taşındı). İkonlar Pillow ile programatik "N" monogram olarak üretildi (matrix tema renkleri) — kullanıcı onayladı, gerçek tasarım sonraya bırakılabilir.
- **`DEPLOY.md` tamamen yeniden yazıldı** — Hetzner+satın-alınmış-domain yerine Oracle Cloud Always Free ARM + DuckDNS. **Oracle'a özgü güvenlik duvarı tuzağı** (belgeye özellikle vurgulandı): VCN Security List `ufw`'den AYRI ve ONA EK — ikisi de açılmadan port erişilemez kalır; bu `ufw` adımından ÖNCE anlatılmalı yoksa saatlerce yanlış yerde debug edilir. A1.Flex kapasitesi sık "Out of host capacity" verir (hesap sorunu değil — her Availability Domain'i dene + saatler/günler içinde tekrar dene). Reserved (statik) public IP mutlaka ayrılmalı (ephemeral IP restart'ta değişir).
- **Dependabot kurulumu** — `.github/dependabot.yml` bu commit'te eklendi (bkz. v2.0 madde 7).
- **`/ws/feed` bağlantı limiti** (v1.17 denetiminde bilinçli ertelenmişti) — `WebSocketNotifier` artık per-user (`ws_max_connections_per_user`, varsayılan 5) + global (`ws_max_total_connections`, varsayılan 500) tavan uyguluyor. `can_accept(user_key)` router'da `accept()`'ten ÖNCE soruluyor (yukarıdaki v1.14 gotcha'sıyla aynı desen — reddedilen bağlantı yine de `accept()` + `close(code=1013, reason="Too many concurrent connections")` ile kapatılıyor, aksi halde gerçek tarayıcı close code'u göremez). `main.py`'de `settings.ws_max_connections_per_user`/`ws_max_total_connections`'tan inject ediliyor. Test: `tests/adapters/test_websocket.py` — per-user limit, global limit, disconnect sonrası slot'un geri açılması.
- **Test:** 517 → 521 (Redpanda migrasyonu sonrası tam paket koşturuldu, `tests/infrastructure/test_settings.py`'deki tek assertion redpanda'ya güncellendi, başka hiçbir test dokunulmadı — hepsi protokol-agnostik mock/stub kullanıyordu). `docker compose config --quiet` ile her iki compose dosyası YAML olarak doğrulandı; gerçek container ayağa kalkışı (Redpanda healthcheck dahil) bir sonraki oturumda `docker compose up -d` ile bir kez doğrulanmalı (bu oturumda Docker daemon çalışmıyordu).
- **KAPSAM DIŞI (bilinçli):** App Store/Play Store yok — sadece PWA. iOS'ta App Store'a çıkmanın ücretsiz yolu yok ($99/yıl zorunlu, istisnasız); Android Play Store tek seferlik $25 ama şimdilik önceliksiz.

**✅ v1.19 — public `/news/search` kota atlatma kapatıldı (23 Temmuz 2026, tamamlandı):**
- v1.17 denetiminde "ürün kararı" diye ertelenmişti: kimliksiz `/news/search` sadece IP-bazlı `30/dakika` ile korunuyordu, günlük tavan yoktu → teorik ~43k istek/gün (Free tier'ın vaat ettiği 100/gün'ün çok üzerinde), landing sayfası demosu bahanesiyle script'le tüketilebilirdi.
- Çözüm: `@limiter.limit("30/minute;200/day")` (`news_router.py::search_news`, slowapi/`limits` kütüphanesinin `;` ile çoklu limit sözdizimi). 200/gün gerçek bir demo ziyaretçisinin asla dokunmayacağı ama otomasyonu anlamsızlaştıran bir eşik — IP paylaşımlı ağların (ofis/mobil operatör NAT'ı) meşru kullanıcıları yanlışlıkla engellememesi için Free tier'ın kayıtlı-kullanıcı limitinden (100/gün) bilinçli olarak daha yüksek tutuldu.
- **Test deseni:** Gerçek 200 HTTP isteği atıp limiti tüketmek yerine (slowapi'nin in-memory limiter state'i tüm test session'ı boyunca paylaşılır — bkz. v1.17 notu, böyle bir test suit'in geri kalanını kirletirdi) `limiter._route_limits["<module>.<func>"]` içindeki kayıtlı `Limit` nesneleri doğrudan denetlendi (`test_public_search_has_daily_quota_cap_registered`, `tests/adapters/test_tier_gating.py`). **Genel kural: slowapi ile korunan bir route'un limit DEĞERİNİ (sayısını/penceresini) doğrulamak istediğinde, HTTP döngüsüyle tüketmek yerine `limiter._route_limits` üzerinden statik olarak oku** — hem hızlı hem paylaşılan test-session state'ini kirletmiyor.
- **Test:** 521 → 522.

**✅ Redpanda migrasyonu GERÇEK container'larla ilk kez doğrulandı + iki altyapı bug'ı bulunup düzeltildi (23 Temmuz 2026, aynı oturum):**
- **Bağlam:** v1.18'de Kafka+Zookeeper → Redpanda geçişi yapılmıştı ama Docker daemon o oturumlarda hiç çalışmıyordu, doğrulama sadece `docker compose config --quiet` (YAML syntax) ile yapılabilmişti — gerçek container ayağa kalkışı/healthcheck HİÇ test edilmemişti (CLAUDE.md'de bilinçli olarak "sonraki oturumda doğrulanmalı" notu vardı). Kullanıcı Docker Desktop'ı açınca bu oturumda ilk kez gerçek doğrulama yapıldı.
- **Bulgu 1 — hayalet Kafka/Zookeeper container'ları:** Docker Desktop açılışında `docker ps` beklenmedik şekilde `nexstream_kafka`+`nexstream_zookeeper`'ı (healthy, "2 hafta önce" oluşturulmuş) `nexstream_engine`/`worker`/`db` (yeni container'lar) ile YAN YANA çalışır gösterdi — ama `nexstream_redpanda` HİÇ YOKTU. Kök neden: compose dosyası v1.18'de değişmiş (redpanda eklenmiş, kafka/zookeeper silinmiş) ama o değişiklikten beri kimse gerçek `docker compose up -d` çalıştırmamıştı; Docker Desktop yeniden başlayınca `restart: unless-stopped` politikalı ESKİ container'ları (compose dosyasından bağımsız, sadece Docker'ın kendi restart mekanizmasıyla) diriltti. **Genel ders: bir compose dosyasını değiştirdikten sonra `docker compose down` çalıştırmadan bırakırsan, Docker Desktop bir sonraki açılışında ESKİ (artık dosyada olmayan) container'ları sessizce diriltebilir — "docker ps" çıktısı her zaman güncel compose config'i yansıtmaz.** Çözüm: `docker compose down` (proje container'larını durdurdu) + `docker rm -f nexstream_kafka nexstream_zookeeper` (compose dosyasında artık olmadıkları için `down` onları görmedi) + `docker compose up -d` (redpanda dahil TÜM stack'i compose dosyasına göre sıfırdan oluşturdu). Sonuç: **`nexstream_redpanda` healthcheck'i GEÇTİ** — migrasyon artık gerçek container'larla doğrulanmış durumda.
- **Bulgu 2 — `hf-xet` indirme tıkanması (app container ilk açılışta unhealthy kalıyordu):** `nexstream_engine` ilk açılışta `/health` hiç 200 dönmüyordu (4+ dakika sonra unhealthy). Log'lar `SentenceTransformer modeli yükleniyor...`'da donmuş görünüyordu. `docker exec` ile HF cache dizini incelendi: indirme **52KB'da tıkanıp kalmıştı** (restart sonrası bile aynı nokta — rastgele değil, deterministik). Kök neden: `huggingface_hub` 0.36.2 + kurulu `hf-xet` 1.5.0 paketi, model repo'su Xet depolama backend'ine taşınmış olduğu için varsayılan olarak yeni "Xet" protokolünü kullanıyor; bu ortamda (Docker Desktop network + ISP kombinasyonu) Xet transferi anlık kilitleniyor, ama klasik düz HTTPS GET (`urllib` ile doğrudan test edildi) sorunsuz çalışıyor. **Çözüm:** `docker-compose.yml` + `docker-compose.prod.yml`'deki `app` ve `worker` servislerine `HF_HUB_DISABLE_XET=1` env var'ı eklendi — klasik indirme yoluna zorluyor. Düzeltme sonrası indirme aktif ilerledi (52KB → 141MB → 272MB → 461MB, ~65MB/dk) ve ~470MB'lık model 5 dakikada tam indi, `/health` `{"status":"ok","db":"ok","kafka":"ok","chromadb":"ok","indexed_articles":4530}` döndü. **Genel ders: `sentence-transformers`/`huggingface_hub` kullanan HERHANGİ bir Docker imajında ilk model indirmesi tıkanırsa (ilerlemesiz, deterministik takılma), önce `hf-xet` paketinin kurulu olup olmadığını kontrol et — kuruluysa `HF_HUB_DISABLE_XET=1` ile klasik indirmeye zorlamak hızlı ve güvenli bir ilk deneme.** Bu, Oracle VPS'e (farklı ağ/ISP) deploy edilirken de karşılaşılabilecek bir risk — DEPLOY.md'ye not düşülmeli.
- **Sonuç:** Tam stack (redpanda, db, chromadb, redis, app, worker, scheduler, frontend, adminer) gerçek container'larla sıfırdan ayağa kaldırıldı ve sağlıklı çalıştığı doğrulandı — v2.0 deploy öncesi en kritik doğrulanmamış varsayım artık kapandı. README için gerçek çalışan uygulamadan Playwright ile ekran görüntüleri alındı (`docs/screenshots/`: landing.png, landing-starwars-theme.png, dashboard.png, search.png, theme-picker.png — demo hesap `nxs-readme-demo-*@gmail.com` ile, `example.com` gibi MX kaydı olmayan domain'lerin kayıtta e-posta-deliverability kontrolüne (v1.14) takılıp 400 döndüğü de bu sırada canlı doğrulandı).

**✅ v1.14 — Tier-gating gerçek yapıldı + canlı testte bulunan auth bug'ları (20 Temmuz 2026, tamamlandı):**
- **Tier-gating** — `domain/models/user.py`'a `TIER_SEARCH_RESULT_CAP` (Free 10/Pro 50/Enterprise 200) + `tier_at_least()` eklendi. `SearchRequest.n_results` şema tavanı 50→200 çıkarıldı (Enterprise için), asıl kısıtlama endpoint'te tier'a göre `min()` ile uygulanıyor — hem `/api/v1/news/search` (gerçek kullanıcı tier'ı) hem public `/news/search` (her zaman Free tavanı, landing demosu). `/api/v1/news/{id}/related` ve `/ws/feed` artık Pro+ ister (403 / WS close 1008). `subscription_router.py`'deki `frequency=instant` — Subscriber email-bazlı ve User'dan bağımsız olduğu için (mimari not, önceden çözülmemişti) yetki kontrolü aynı e-postayla kayıtlı bir User'ın tier'ına bakarak yapılıyor (`_assert_instant_allowed`, `UserRepository.get_by_email`); kayıtsız/Free e-posta instant isteyemez, daily/never her zaman serbest.
- **WebSocket close code — gerçek tarayıcıda bulunan gotcha:** İlk yazımda `accept()` ÇAĞIRMADAN `close(code=1008)` çağrılıyordu — Starlette `TestClient` bunu doğru `WebSocketDisconnect(code=1008)` olarak yakalıyor (testler yeşil geçti) ama GERÇEK bir tarayıcı açılış handshake'i (101 Switching Protocols) hiç tamamlanmadığı için özel close code'u HİÇ GÖREMİYOR, sadece genel "1006 abnormal closure" görüyor — Monitor'ün `ws` source'uyla gerçek stack'e canlı bağlanıp yakalandı. Düzeltme: ÖNCE `accept()` SONRA `close(1008)` — handshake tamamlanıyor, close frame'i gerçek kodla gidiyor. **Genel kural: bir WebSocket route'unu reddederken `accept()`'i atlamak yerine `accept()` + hemen `close(code=...)` kullan**, yoksa istemci tarafında close code'a bakan hiçbir mantık (retry/lock ayrımı gibi) gerçek dünyada çalışmaz — sadece ASGI-seviyeli test client'lar bu farkı gizler.
- **Frontend tier-aware UX** — `LiveTicker` artık Free kullanıcıda `/ws/feed`'e hiç bağlanmayı denemiyor (`useLiveFeed(enabled)` parametresi) ve sunucu 1008 ile reddederse sonsuz 4sn'lik reconnect döngüsüne girmek yerine "locked" durumuna geçip yükseltme çağrısı gösteriyor. `NewsCard`'ın "İlgili haberler" butonu Free'de PRO rozetiyle işaretli, tıklanınca boşuna 403 istemek yerine upsell kartı gösteriyor. Arama sayfası Free kullanıcı 10'un üzerini seçerse (sunucu sessizce kırpacağı için) açıklayıcı bir ipucu gösteriyor.
- **Canlı testte kullanıcının bulduğu 3 auth bug'ı:** (1) Login'de eksik e-posta (`.com` unutulmuş) girilince "⚠ [object Object]" hatası — kök neden `frontend/lib/api.ts::req()`'in FastAPI/Pydantic doğrulama hatalarının `detail` alanının bazen STRING değil `[{type,loc,msg,...}]` DİZİSİ olabileceğini hesaba katmaması (`new Error([{...}])` → `String([obj])` → "[object Object]"). Yeni `extractErrorMessage()` yardımcısı dizi/obje/string hepsini okunabilir mesaja indirgiyor. (2) Moderatör OLMAYAN giriş yapmış bir kullanıcı `/admin/users`'a doğrudan gidince "API anahtarı gir" isteniyordu (yanlış — anahtarı yok/olmamalı) — `admin/layout.tsx` artık `user && !is_moderator` durumunda tabs/children'ı hiç render etmeyip net bir "403 — Erişim reddedildi" ekranı gösteriyor; API key girişi sadece OTURUMSUZ erişim için sayfa içinde kalıyor. (3) Kayıtta `muz@muz.com` gibi hiç mail almayan domain'ler kabul ediliyordu — `auth_router.py::register`'a `email_validator.validate_email(email, check_deliverability=True)` ile DNS/MX kontrolü eklendi (`_assert_deliverable_email`), sadece definitif "domain mail almıyor" sonucunda 400 döner, DNS sorgusu ağ/timeout yüzünden patlarsa KAYDI ENGELLEMEZ (fail-open). **Bilinçli sınır (o oturumda):** gerçek bir domain + uydurma kullanıcı adını (örn. `rastgele123@gmail.com`) YAKALAMAZ — ✅ v1.15'te e-posta doğrulama linkiyle çözüldü (bkz. aşağıdaki v1.15 bloğu).
- **Docker disk temizliği (aynı oturum, proje ile ilgisiz ama not düşülmeye değer):** `docker builder prune` bu sistemde (Docker Desktop + buildx) hiçbir şey temizlemedi — buildx kendi cache store'unu ayrı tutuyor, `docker buildx prune -af` gerekiyor. 11.33GB boşta duran build cache + 671.8MB bağlantısız volume temizlendi, çalışan container'lara dokunulmadı. **CLAUDE.md'deki "docker builder prune -f && docker volume prune -f" komutu bu Docker Desktop kurulumunda YETERSİZ — buildx cache için `docker buildx prune -af` de eklenmeli.**

**✅ v1.15 — E-posta doğrulama akışı (21 Temmuz 2026, tamamlandı):**
- **Ne yapıldı:** Kayıtta gönderilen onay linki. Gating **yumuşak+orta karma** (kullanıcı kararı): doğrulanmamış kullanıcı Free tier'da TAM erişime sahip (hiçbir endpoint kilitlenmedi); sadece `/billing/checkout` (Pro/Enterprise'a yükseltme — hem dev-mode hem gerçek Stripe yolu) `email_verified=true` ister, aksi halde 403. `User.email_verified` (varsayılan `False`) + `EmailVerificationToken` (PasswordResetToken ile birebir aynı şekil: user_id/token/expires_at/used) `domain/models/user.py`'a eklendi. TTL 24 saat (`EMAIL_VERIFICATION_TTL_MINUTES`, varsayılan 1440 — şifre sıfırlamadan çok daha uzun, kayıt sonrası hemen tıklama zorunluluğu yok). Yeni endpoint'ler: `POST /auth/resend-verification` (5/dk rate limit, oturum ister, zaten doğrulanmışsa no-op) + `POST /auth/verify-email` (20/dk, oturum GEREKMEZ — reset-password ile aynı desen, başka cihaz/tarayıcıdan da çalışır). `register` artık `_send_verification_email()` çağırır — **best-effort/fail-open**: mail gönderimi patlarsa (ağ hatası, Resend down) kayıt YİNE DE başarılı olur, sadece loglanır (forgot-password'daki desenle tutarlı).
- **Migration:** `migrations/v1_15_email_verification.sql` — `users.email_verified` ALTER + `email_verification_tokens` tablosu. Zaten ücretli kademedeki kullanıcılar (dev-mode demo yükseltmeleri dahil) `UPDATE users SET email_verified=TRUE WHERE tier != 'free'` ile geriye dönük kilitlenmekten korundu — yeni bir gating kolonu eklerken var olan "ayrıcalıklı" satırları grandfather'lamayı unutma.
- **Frontend:** `frontend/app/auth/verify-email/page.tsx` (mail linkinin hedefi — mount'ta otomatik doğrular, form yok), `components/EmailVerifyBanner.tsx` (doğrulanmamışsa `DashboardShell` + `account` sayfasında görünen, session-only dismiss'li yumuşak nag banner + yeniden gönder butonu). `account` sayfasındaki yükseltme kartı `email_verified=false` iken butonları hiç göstermiyor (boşuna 403 istemek yerine proaktif ipucu).
- **Gotcha — Resend sandbox kısıtı (canlı testte bulundu):** Resend API key'i gerçek/prod modda bile olsa, **doğrulanmış bir domain yoksa** (`resend.com/domains`) sadece hesap sahibinin KENDİ e-postasına gönderim yapılabiliyor — başka bir adrese denemek `403 "You can only send testing emails to your own email address"` ile patlıyor. Bu SADECE bu özelliğe değil, `ResendEmailAdapter`'ın TÜM gönderimlerine (digest, alert, welcome, reset, verify) uygulanıyor. Canlı uçtan-uca test bu yüzden DB'den token'ı elle okuyup (`docker exec nexstream_db psql ... SELECT token FROM email_verification_tokens`) `/auth/verify-email`'e curl ile geçmek zorunda kaldı. **Prod'a domain doğrulaması yapılmadan çıkılırsa gerçek kullanıcılara (hesap sahibi hariç) hiçbir mail gitmez** — v2.0 launch checklist'ine eklenmeli.
- **Test kalıbı — yeni gating boolean'ı eklerken:** `User.email_verified` varsayılanı `False` olduğu için, `billing_router` testlerindeki `_make_user()` yardımcıları (`test_billing_router.py`, `test_billing_dev_mode.py`) checkout'u zaten test eden HER senaryoda sessizce 403'e düşürdü (6 test kırıldı). Düzeltme: her iki dosyadaki `_make_user()`'a `email_verified=True` varsayılanı eklendi + gate'i özel test eden 2 yeni test (`email_verified=False` ile). **Genel kural: paylaşılan bir domain modeline (User gibi) yeni bir "varsayılanı False/kısıtlayıcı" alan eklerken, o modeli kullanan TÜM test dosyalarındaki factory helper'ları tara** — sadece değiştirdiğin router'ın testleri değil.
- **Backend:** 494 test (482'den +12: register/resend/verify-email için 10 yeni test `test_auth_router.py`'de, +2 billing gate testi).

**✅ v1.17 — KAPSAMLI GÜVENLİK DENETİMİ + sertleştirme (21 Temmuz 2026, kritik/yüksek tamamı kapatıldı):**
Canlıya çıkış öncesi 5 eksende (auth/oturum, injection, secrets/altyapı, iş mantığı/DoS, bağımlılıklar) tam denetim yapıldı — 34 kod/config bulgusu + 10 bağımlılık zafiyeti. **Kritik 4 + Yüksek 9 = 13'ünün TAMAMI kapatıldı**, orta/düşükten 9'u daha kapatıldı. Rapor artifact olarak yayınlandı.
- **🔴 EN KRİTİK — sızmış DB şifresi (doğrulandı, aktifti):** `git log --all --full-history -- .env` üç commit gösteriyordu; `33eb133`'te gerçek bir `DB_PASSWORD` değeri açıkça vardı. "Remove .env from git" commit'i blob'u geçmişten SİLMEZ — `git show 33eb133:.env` hâlâ çalışıyor. Repo `github.com/MaviMakumba/NexStream-News-Engine` **gerçekten public** (auth'suz raw.githubusercontent 200 döndü) VE o şifre **hâlâ kullanımdaydı**. Şifre rotate edildi (`ALTER USER` + `.env`). **Ders: `.env`'i git'ten kaldırmak sızıntıyı çözmez — tek gerçek çözüm rotasyondur.**
- **Prod başlangıç guard'ı (yeni, merkezi savunma):** `settings.py::_reject_unsafe_production_config` — `ENVIRONMENT=production` iken şu dördünden biri bile zayıfsa uygulama AÇILMAYI REDDEDER: `API_KEY` varsayılan/boş, `BILLING_DEV_MODE=true`, `CORS_ORIGINS="*"`, `SESSION_COOKIE_SECURE=false`. Dev'de `environment` varsayılanı `"development"` olduğu için hiç çalışmaz. Prod compose `ENVIRONMENT=production` set eder. Bu, denetimdeki 4 ayrı "operatör unutursa" riskini tek noktada kalıcı olarak kapatır.
- **`docker-compose.prod.yml`'de `CORS_ORIGINS` SATIRI HİÇ YOKTU** — `.env`'e yazsan bile etkisi olmuyordu, uygulama `"*"` + `allow_credentials=True` ile açılıyordu. Eklendi. `GRAFANA_PASSWORD` de `:-nexstream` fallback'inden `:?` (deploy'u sert durduran) forma çevrildi — unutulursa artık herkesçe bilinen şifreyle prod'a çıkılamıyor.
- **Auth sertleştirme:** `/auth/login` + `/auth/register` rate limitsizdi (brute-force'a tamamen açık) → 15/dk. Login'de kullanıcı bulunamayınca bcrypt hiç çalışmıyordu → yanıt süresinden kayıtlı e-posta enumerate edilebiliyordu; `_DUMMY_PASSWORD_HASH` ile süre eşitlendi. API key karşılaştırması `==` → `secrets.compare_digest` (`auth.py::api_key_matches`, auth_utils da paylaşıyor).
- **TOCTOU yarışı:** reset/verification token'larında SELECT + ayrı UPDATE vardı; eşzamanlı iki istek aynı token'ı kullanabiliyordu. `mark_*_token_used` artık tek `UPDATE ... WHERE used=false` + rowcount döner (`-> bool`), router'lar token'ı ÖNCE atomik tüketip SONRA işlem yapıyor.
- **Gelir kaçağı:** legacy `/news/{id}/related` hiç tier kontrolü yapmıyordu — `/api/v1` versiyonu 403 dönerken bu route pricing'in "Pro" dediği ilişki grafını herkese bedava veriyordu. Aynı Pro+ kilidi eklendi.
- **E-posta HTML injection:** `email_adapter.py`'de haber başlığı/özeti/kaynağı ve sponsor alanları `html.escape()` OLMADAN f-string ile HTML'e gömülüyordu. Ele geçirilmiş bir RSS kaynağı phishing linkini TÜM abonelere gönderebilirdi. Hepsi escape'lendi + 3 regresyon testi.
- **Rate limit boşlukları kapatıldı:** `/subscriptions/` (email-bombing vektörüydü, 5 endpoint'in hiçbirinde limit yoktu) 10/dk, `/news/reindex` (tam-tablo senkron işlem, limitsizdi) 2/dk, `/health` (her istek 3 backend'e gerçek bağlantı açıyor) 60/dk, `/account/api-key` 10/dk, Stripe webhook 60/dk, checkout 20/dk.
- **nginx:** CSP + Permissions-Policy eklendi (ikisi de tamamen eksikti); Grafana (5r/s) ve frontend (60r/s) için `limit_req` zone'ları eklendi — önceden sadece `/api/` korumalıydı. CSP'de `'unsafe-inline'` MECBUREN açık (proje inline style objesi kullanıyor + Next.js hydration inline script gömüyor); nonce'a geçiş ayrı bir iş.
- **Container'lar root çalışıyordu** → `Dockerfile`/`Dockerfile.light`'a `USER appuser` eklendi (`--create-home` şart: SentenceTransformer `~/.cache/huggingface`'e yazıyor).
- **Bağımlılıklar:** next 14.2.29→14.2.35 (WS-upgrade SSRF + Server Components DoS), fastapi 0.129→0.139.2, starlette 0.52.1→1.3.1 (host/path validation), prometheus-fastapi-instrumentator 7.1→8.0.2 (starlette 1.x uyumu için ZORUNLUYDU), pydantic-settings/python-dotenv/requests/lxml/pytest. `requirements-light.txt`'te de aynı eski pin'ler vardı (scheduler container'ı savunmasızdı) — atlanmamalı. **Kalan 2 (bilinçli):** `chromadb` (upstream'de fix YOK, ağ izolasyonuyla korunuyor, izlenmeli) ve `transformers` (RCE'ler saldırgan-kontrollü model repo'su gerektiriyor; bu proje sabit yerel embedding modeli kullanıyor → gerçek risk düşük).
- **KAPATILMAYANLAR (bilinçli, sonraki oturum):** ~~`/ws/feed` bağlantı sayısı sınırsız~~ — ✅ **22 Temmuz 2026'da v1.18'de kapatıldı** (detay aşağıda, `WebSocketNotifier.can_accept`); ~~public `/news/search` kota atlatma~~ — ✅ **23 Temmuz 2026'da kapatıldı** (detay aşağıda, "v1.19" notu); ~~yedekler şifresiz/offsite değil~~ — ✅ **v1.18'de zaten kapatılmış** (GPG opt-in şifreleme + rclone opt-in offsite upload, `infra/backup/backup.sh` — sadece prod'da `BACKUP_GPG_PASSPHRASE`/`RCLONE_REMOTE` set edilmesi gerekiyor, deploy checklist'ine eklenmeli); token'lar DB'de düz metin (belgelenmiş sadelik tercihi); `/docs` prod'da açık (yol haritasındaki "API dökümantasyon portalı" ürün özelliğiyle çelişmesin diye BİLİNÇLİ bırakıldı).
- **Test:** 505 → 517 (+12: settings guard 6, timing-safety 1, related tier-gate 2, email escape 3).

**✅ v1.16 — Ham veri export + dashboard canlı liste enjeksiyonu (21 Temmuz 2026, tamamlandı):**
- **Ham veri export — kapsam netleştirme (kullanıcı kararı):** Pricing sayfası zaten "Ham veri export"u SADECE Enterprise vaat ediyordu (Pro değil) — bu okunarak gating buna göre yapıldı. Format: hem CSV hem JSON (`?format=csv|json`, varsayılan csv). Üst sınır: `EXPORT_MAX_ROWS` (varsayılan 20000) — runaway sorgudan korur. Rate limit: dakikada 10 (diğer `/api/v1` endpoint'lerinden — search 30/dk, related 60/dk — kasıtlı olarak daha sıkı, çünkü tek export isteği binlerce satıra denk gelir).
- **Endpoint:** `GET /api/v1/news/export` (`news_router_v1.py`) — filtreler: `source`/`sentiment`/`topic`/`min_quality` (mevcut `/news` endpoint'iyle aynı) + YENİ `date_from`/`date_to` (YYYY-MM-DD, dahil). Tarih filtresi `published_at`e uygulanır, NULL ise `created_at`e düşer (ChromaDB metadata fallback'iyle aynı desen — v1.4 öncesi scrape'lerde published_at boş olabilir). Enterprise-only: `user.tier != ENTERPRISE` → 403 (Pro dahil herkese kapalı — `tier_at_least` DEĞİL, tam eşitlik).
- **Backend:** `NewsRepository.get_articles_for_export()` (port'a eklenmedi, `get_news_paginated` gibi sadece concrete metod — bu repo'daki mevcut tutarsız-ama-kasıtlı desen), `NewsService.export_articles()` ince passthrough. Response `NewsResponse` Pydantic şeması üzerinden üretilir (`model_validate(article).model_dump(mode="json")`) — hem CSV hem JSON aynı veri şeklini paylaşır.
- **Bug bulundu ve düzeltildi (kendi testimde yakalandı):** İlk yazımda `entities` alanı HEM CSV HEM JSON çıktısında JSON-string'e çevriliyordu (CSV hücresine sığması için gerekli ama JSON formatında YANLIŞ — iç içe obje olması gerekirken çift-encode edilmiş string dönüyordu). `_export_row()` (native dict, JSON için) ve `_export_csv_row()` (string'e çevrilmiş, CSV için) olarak ikiye ayrıldı. **Genel ders: aynı satır verisini birden fazla formata (CSV+JSON) seren kodda, format-özel dönüşümleri (flatten/stringify) ortak satır üretici fonksiyondan AYRI tut** — yoksa bir format diğerini kirletir, ve bu tür hatalar sadece nested/complex alanlarda (burada `entities` dict'i) ortaya çıktığı için düz alanlı testler yakalayamaz.
- **CSV detayı:** `utf-8-sig` (BOM'lu) encode edilir — Excel BOM'suz UTF-8 CSV'de Türkçe karakterleri (İ/ş/ğ) bozuk gösterir. `Content-Disposition: attachment` + zaman damgalı dosya adı (`nexstream_export_YYYYMMDD_HHMMSS.csv|json`).
- **Test tuzağı — paylaşılan slowapi rate limit state'i:** İlk yazımda `5/dk` seçildi ama `test_tier_gating.py`'deki 7 export testi (blocked×3 + allowed×2 + invalid-format + max-rows) AYNI dakika penceresinde art arda koşunca kendi limitine takılıp 429 döndü (`mock_service.export_articles.call_args` `None` kaldı → `TypeError`). Kök neden: `tests/conftest.py`'deki `app_client` fixture'ı her testte `src.main`'i `importlib.reload()` eder ama `src.adapters.api.limiter`'daki `Limiter` singleton'ı YENİDEN YÜKLENMEZ (transitive reload yok) — yani slowapi'nin in-memory sayaçları TÜM test session'ı boyunca paylaşılır, `key_func=get_remote_address` TestClient'ta hep "testclient" döner. **Genel kural: yeni bir rate-limited endpoint'e birden fazla test yazarken, o dosyadaki TOPLAM çağrı sayısının seçtiğin dakikalık limitin altında kaldığından emin ol** (ya limiti gevşet ya test sayısını/tekrarını azalt) — limiter state test'ler arası resetlenmiyor. Limit 10/dk'ya çıkarıldı (7 çağrıya rahat marj, hâlâ search/related'den belirgin şekilde sıkı).
- **Frontend:** `account` sayfasında Enterprise-only export kartı (format toggle CSV/JSON + indir butonu). `lib/api.ts::downloadExport()` — plain `<a href>` yerine `fetch()`+Blob kullanır (403/hata durumunda tarayıcı hata sayfası yerine okunabilir `ApiError` fırlatsın diye), `Content-Disposition`'dan dosya adını okur.
- **Backend:** 505 test (494'ten +11: 7 tier-gating/router testi `test_tier_gating.py`, 4 filtre/tarih-aralığı testi `test_news_repository.py`).

**✅ Dashboard "Son Haberler" listesi artık WebSocket'ten canlı besleniyor (aynı oturum, kullanıcı sorusu üzerine):**
- **Bulunan boşluk:** `LiveTicker` (üst şerit) kendi `useLiveFeed()` bağlantısını tutuyordu ama `dashboard/page.tsx`'teki asıl haber listesi SADECE `fetchNews()` REST çağrısıyla besleniyordu — WS'ten yeni haber gelince şeritte görünüyordu ama listeye girmiyordu, F5 gerekiyordu.
- **Çözüm:** `lib/live-feed-context.tsx` (yeni) — `useLiveFeed()` artık `DashboardShell`'de (dashboard segmentinin `layout.tsx`'i, `/dashboard` ↔ `/dashboard/search` arası persist olur) TEK yerden açılıp `LiveFeedProvider` ile paylaşılıyor; `LiveTicker` de `dashboard/page.tsx` da aynı bağlantıyı `useLiveFeedContext()` ile tüketiyor (önceden iki ayrı WS bağlantısı açılabilirdi, bug olarak fark edilmedi ama gereksizdi). `dashboard/page.tsx`'te yeni bir `useEffect`, `liveArticles[0]` değişince (yeni haber) onu `Article` şekline çevirip listenin BAŞINA ekliyor — id bazlı dedup (`seenLiveIds` ref, mount'ta mevcut feed id'leriyle seed'lenir ki eski oturumdan kalan haberler retroaktif enjekte edilmesin) + aktif filtrelerle (sentiment/topic/source) uyum kontrolü. **`min_quality` filtresi aktifken enjeksiyon TAMAMEN atlanır** — WS payload'ında `quality_score` yok (bkz. `websocket_notifier.py::broadcast_article`), doğrulayamadığımız bir filtreyi sessizce ihlal etmemek için.
- **Ders:** `NewsCard` bileşeni `article.content`'i hiç render etmiyor (sadece `article.id` ile `fetchRelated()` çağırıyor) — bu yüzden WS payload'ının eksik alanları (`content`, `entities`, `quality_score`, `credibility_score`) enjekte edilen kartlarda sorun çıkarmadı, sadece o kartlarda entity chip/kalite rozeti görünmüyor (zaten analiz henüz tazeyse normal).

**✅ v1.12 kalan maddeleri: responsive + erişilebilirlik + tema perf profilleri (20 Temmuz 2026, tamamlandı):**
- **Responsive tarama:** `admin/sponsors` sayfasında liste+form grid'i `canManage ? "1fr 1fr" : "1fr"` idi — dar ekranda her zaman yan yana 2 sıkışık kolon kalıyordu, hiç tek kolona düşmüyordu. `repeat(auto-fit, minmax(280px, 1fr))`'e çevrildi (dashboard/landing'teki feature/pricing grid'leriyle aynı desen). `account` sayfasındaki iki grid (plan/limit `1fr 1fr`, usage KPI `repeat(3,1fr)`) `minmax(0,1fr)` ile CSS Grid blowout'a karşı sertleştirildi — bare `1fr` track'ler içerik min-content'ini aşınca grid'i konteynerinden taşırıp sayfayı yatay kaydırmaya zorlayabiliyordu (klasik mobil CSS Grid hatası). Arama formuna `flexWrap` + `minWidth:0` eklendi. Admin `users`/`usage` tabloları zaten `overflowX:auto` sarmalayıcıyla doğru yapılmıştı, dokunulmadı.
- **Erişilebilirlik — kontrast:** `--text3` tokeni **9 temanın HEPSİNDE** WCAG AA eşiğinin (4.5:1, normal metin) altındaydı — hesaplanan gerçek kontrast oranları 2.28 (day/aydınlık tema!) ile 3.32 arasındaydı. Bu token timestamp/section-label gibi UI'da en çok kullanılan metin rengi. Her temanın kendi `text2`/`text3` arasında hue-tutarlı, ~4.5:1'e ulaşan yeni bir `text3` hesaplandı (Node ile WCAG relative-luminance formülüyle) ve `globals.css`'teki 9 blokta güncellendi. **İkinci tur (kullanıcı "bazı temalar hâlâ karanlık/okunaksız duruyor, Star Wars karanlık olsa da en okunaklısı" diye bildirince):** `--accent` kontrastı temalar arası inanılmaz dağınıktı (Star Wars'ın sarısı 16.60 iken Spiderman'ın kırmızısı sadece 4.41, Wolfenstein'ınki 4.22 — ikisi de AA eşiğinin altında; kırmızı tonlar luminance formülünde düşük ağırlıklı [0.2126] olduğu için göze parlak görünseler de kontrastı düşük çıkıyor). Kullanıcının Star Wars övgüsü bu hesaplamayı canlı doğruladı. Spiderman/Wolfenstein'ın `--accent`'i, HİÇBİR yerde kullanılmadığı ortaya çıkan kendi `--accent-h` (hover için tanımlanmış ama hiç bağlanmamış açık ton) değişkenine %50 harmanlanarak ~5.0'a çekildi. Ayrıca Kurumsal rozetinin metin rengi olan Godfather'ın `--accent2`'si (2.65 — felaket) beyaza %30 harmanlanarak ~5.1'e çekildi. `--accent-soft`/`--accent-line`/`--glow` gibi türetilmiş rgba() değerleri bilinçli olarak dokunulmadı (düşük alpha'da fark edilmez, ayrı bir refactor gerektirir).
- **Erişilebilirlik — klavye/aria:** Navbar dropdown'ları (ayarlar/kullanıcı/mobil menü) artık `Escape` ile kapanıyor (önceden sadece backdrop tıklaması vardı). Ayarlar/kullanıcı-menü butonlarına `aria-haspopup`/`aria-expanded`/`aria-label`, tema/dil/perf seçici butonlarına `aria-pressed`, aktif nav linkine `aria-current="page"`, arama geçmişi "×" butonuna `aria-label` eklendi. `LiveTicker` artık hover/focus'ta otomatik rotasyonu durduruyor (WCAG 2.2.2 "Pause, Stop, Hide" — 5sn'de bir kendiliğinden değişen içerik durdurulabilmeli).
- **Tema performans profilleri:** `settings-context.tsx`'e `perf: "low"|"high"` eklendi (`nxt_perf` localStorage, `<html data-perf>`, tema gibi `useIsomorphicLayoutEffect` ile senkron uygulanıyor). 8 canvas efekti de (`lib/theme/effects/*`) yeni `density()` helper'ı (`shared.ts`) ile parçacık sayısını "low"da yarıya indiriyor — en büyük kazanç `WebStrands`'in O(n²) cross-link geçişinde (node sayısı yarılanınca iş dörtte bire iniyor) ve `FilmGrain`'in per-frame `putImageData` boyutunda. `ThemeBackground` artık `theme` yanında `perf`'i de key'e alıyor ki toggle anında etkili olsun (resize beklemeden). Navbar ayarlar panelinde + mobil menüde toggle var.
- **Auth loading state tutarlılığı:** `DashboardShell`'in markalı yükleme ekranı (NexStream gradient + nabız noktası) `AuthLoadingScreen` bileşenine çıkarıldı, `account` sayfası da (önceden `isLoading` iken düz `return null` = boş beyaz flaş) artık aynısını kullanıyor.
- **Canlı testte kullanıcının bulduğu 2 bug (aynı oturum):** (1) Navbar'da dile göre `Kurumsal`→`Enterprise` geçince (özellikle Matrix'in monospace/Godfather'ın serif fontuyla, aynı metin daha geniş basılıyor) tier rozeti kullanıcı butonunun dar `maxWidth`'i içine sığmayıp SATIR KIRIYORDU (◆ ikonu yukarı kayıyordu) — kök neden `.badge` class'ında `white-space`/`flex-shrink` koruması hiç yoktu. `globals.css`'e `.badge { white-space: nowrap; flex-shrink: 0; }` eklendi (TÜM rozetler için genel/kalıcı düzeltme), Navbar kullanıcı butonunun `maxWidth`'i 240→280'e çıkarıldı, isim span'ı sacrificial (küçülebilir) tek eleman olarak bırakıldı. (2) Landing sayfasındaki istatistik satırı (`825+ Haber İndekslendi` vb.) TR/EN dil değişiminde KAYIYORDU çünkü her sütunun genişliği içeriğe göre belirleniyordu ve etiket uzunlukları dile göre farklıydı (`justifyContent:center` ile ortalanan grup toplam genişliği değişince tüm satır kayıyordu) — her sütuna sabit `minWidth:160` verilerek düzeltildi.

**✅ WebSocket canlı ticker + landing/navbar UX düzeltmeleri (20 Temmuz 2026, tamamlandı):**
- **WebSocket canlı ticker** — `frontend/lib/useLiveFeed.ts` (yeni): `/ws/feed`'e bağlanan, kopunca 4sn'de bir yeniden bağlanan, son 8 haberi tutan hook. `frontend/components/LiveTicker.tsx` (yeni): Navbar altında canlı/bağlanıyor/koptu durumunu nabız noktasıyla gösteren, 5sn'de bir rotasyonla en güncel haberi sunan şerit; `DashboardShell.tsx`'e bağlandı (`/dashboard` + `/dashboard/search`). Backend tarafı v1.7'den beri hazırdı (`websocket_router.py`/`websocket_notifier.py`), sadece frontend eksikti — gerçek bir scrape sırasında protokol seviyesinde test edildi, mesaj şekli (`type:"article"`/`type:"ping"`) birebir uyuştu.
- **Landing "En Popüler" rozeti bug'ı:** `badge gradient-text` class kombinasyonu + inline `style.background` → `.gradient-text`'in metni `background-clip:text` ile "kestiği" gradyanı eziyordu, metin tamamen transparan kalıyordu (sadece mouse ile seçilince görünüyordu — seçim vurgusu transparan metnin altını gösteriyor — tema fark etmiyordu çünkü sorun renk değil transparanlıktı). Düzeltme: rozete düz `color: var(--accent)` verildi, `gradient-text` class'ı kaldırıldı. **Genel kural: `badge` + `gradient-text` class'larını birlikte kullanma** — biri solid arka plan ister, diğeri arka planı metin gradyanı için kullanır, ikisi çakışır.
- **Navbar artık scroll-yönüne duyarlı (`NavbarImpl.tsx`):** Aşağı kaydırınca `translateY(-100%)` ile gizleniyor, yukarı doğru en ufak kaydırmada (ya da `y<80`, sayfa başına yakınken) anında geri geliyor; ayarlar/kullanıcı/mobil menüsü açıkken gizlenmiyor. **Kök neden — sadece landing sayfasında bozuktu:** `app/page.tsx`'in kök `<div>`'inde `overflowX: "hidden"` vardı (hero'daki dekoratif glow blob'larının taşırdığı yatay overflow'u kesmek için eklenmişti). CSS spec'e göre `overflow-x` görünür-olmayan bir değere ayarlanınca tarayıcı `overflow-y`'yi zorla `auto` yapar, bu da o div'i navbar'ın sticky/scroll hesaplamasının referans aldığı "scroll container"a çevirip sadece o sayfada scroll-hide/sticky davranışını bozuyordu (`DashboardShell.tsx`'te bu satır hiç yoktu, orada sorun yoktu). Düzeltme: kökten kaldırıldı, clip ihtiyacı olan hero `<section>`'a taşındı. **Genel kural: `overflow-x`/`overflow-y`'yi sayfa kökünde değil, ihtiyaç duyan en dar kapsamlı elementte kullan** — kökte kullanmak içindeki `position:sticky` elementlerin referans aldığı scroll container'ı sessizce değiştirir.

**✅ Admin müşteri paneli + rol hiyerarşisi (8 Temmuz 2026, tamamlandı):**
- `GET /admin/users` (`admin_router.py`, `UserRepository.list_users`/`count_users`) + `frontend/app/admin/users/page.tsx` — tüm kullanıcılar, tier, aktiflik ve **`is_paying`** (gerçek Stripe müşterisi mi — `stripe_customer_id` doluluğundan türetilir, dev-mode tier yükseltmesi bunu HİÇ yazmaz, bkz. `billing_router.py`). Admin tab sırası artık Kullanıcılar → Kullanım → Sponsorlar (`admin/layout.tsx`), admin giriş linki `/admin/users`'a yönlendiriyor.
- **v1.13 rol hiyerarşisi (user < moderator < admin)** — v1.11'deki boolean `users.is_admin` kolonu **kaldırıldı**, yerine `users.role` (VARCHAR) geldi (`migrations/v1_13_user_roles.sql`, dev DB'ye elle uygulandı çünkü `create_all` mevcut tabloları ALTER etmez). `domain/models/user.py`'de `UserRole` enum + `role_at_least()`. `auth_utils.py`: `has_admin_role`/`has_moderator_role`/`effective_role`, yeni `require_moderator` dependency (görüntüleme) `require_admin`'in (yazma) yanına eklendi. `admin_router.py` router-level `require_moderator`'a düşürüldü, sponsor CRUD + yeni `PATCH /admin/users/{id}/role` route-level ayrıca `require_admin` ister (kendi rolünü admin'den düşürmeye karşı guard var). `/auth/me` yanıtına `role` + `is_moderator` eklendi, `is_admin` geriye-dönük uyumluluk için korundu (türetilmiş: `role==admin`). Frontend: Navbar/account admin girişi artık `is_moderator`'a bakıyor (moderator da admin panelini görebilir), `admin/users` sayfasında rol sütunu admin için editable `<select>`, moderator için salt-okunur rozet; `admin/sponsors`'ta create-form/deactivate sadece admin'e (`canManage` deseni).
- **ADMIN_EMAILS bootstrap kullanımda:** `.env`'e `ADMIN_EMAILS=<email>` eklenip `docker compose up -d app` (sadece `restart` YETMEZ, env değişkeni yeniden okunmaz) ile ilk admin DB'ye dokunmadan atanır.

**✅ Sponsor tekillik kuralı + email i18n refactor + digest kişiselleştirme (8 Temmuz 2026, tamamlandı):**
- **Sponsor bug'ı (gerçek kullanıcı bulgusu):** `create_sponsor` önceden diğer sponsorları pasife almıyordu — aynı anda 4 sponsor `is_active=true` olabiliyordu, admin paneli `sponsors.find(s=>s.is_active)` ile sadece İLKİNİ gösterip gerisini sessizce gizliyordu ("sponsor ekliyorum ama hiçbir şey değişmiyor" şikayetinin kök nedeni). Düzeltildi: `create_sponsor`/`activate_sponsor` artık diğerlerini otomatik pasife alıyor (`_deactivate_all_active_sponsors`). Yeni: `POST /admin/sponsors/{id}/activate` (süresi geçmemiş pasif sponsoru geri aktifleştir) + `DELETE /admin/sponsors/{id}/permanent` (kalıcı silme, soft-delete'ten ayrı).
- **email_adapter.py tamamen sözlük tabanlı i18n'e geçti** (`_STRINGS`/`_TOPIC_LABELS`, frontend'in `UI[lang]` deseniyle birebir) — kullanıcı `if language=="TR" else` dallanmasının SOLID/Open-Closed ihlali olduğunu belirtti, bu artık projedeki TÜM yeni kod için genel kural (bkz. `[[feedback-clean-code-i18n]]`). Bu refactor sırasında 3 gerçek hata bulundu: sponsor başlığı `if True else` yüzünden dilden bağımsız hep TR basılıyordu; haber konuları (topic) hiç çevrilmiyordu; "aboneliği iptal et" linki hiç doldurulmayan literal `{unsubscribe_url}` placeholder'ıydı (artık gerçek `GET /subscriptions/unsubscribe` linkine gidiyor, tıklanabilir onay sayfası döner — bu route `/{email}` parametreli route'lardan ÖNCE tanımlı olmalı yoksa "unsubscribe" bir email sanılır). `send_alert` artık `EmailPort` sözleşmesinde `language` parametresi alıyor (önceden hep TR sabitti). Digest saati 08:00→09:00 TR (`newsletter_hour_utc` 5→6 UTC).
- **Günlük digest artık gerçekten kişiselleşiyor** — yeni `src/domain/services/subscriber_matching.py` (saf domain fonksiyonu, `matched_keyword`/`has_preferences`/`article_matches_subscriber`) hem `news_service.py::_send_keyword_alerts` hem `newsletter_job.py::_send_digests`'te paylaşılıyor. `_send_digests` artık 60'lık bir aday havuzundan her abone için konu/kaynak/keyword'e uyan haberleri seçiyor; tercih yoksa veya hiç eşleşme yoksa genel havuza düşer (boş mail atılmaz). Türkçe "İ" (U+0130) için özel normalizasyon var — Python'un varsayılan `.lower()`'ı bunu "i" + birleşen nokta işaretine çevirip eşleşmeleri kaçırıyordu.
- Bu üçü canlı olarak gerçek Resend gönderimleriyle test edildi (keyword alert gerçek bir Beşiktaş haberiyle, digest gerçek `_send_digests` çağrısıyla).

**✅ Go-live hazırlık turu (8 Temmuz 2026, tamamlandı):** Aşağıdaki 5 iş bir oturumda bitirildi — detay [[memory: project_nexstream_launch_prep]]:
   - Temel SEO: her segmente `generateMetadata` (server layout split deseni, `DashboardShell.tsx` örneği), `app/robots.ts`, `app/sitemap.ts`.
   - Asgari yasal sayfalar: `/privacy`, `/terms` (`lib/legal-content.ts`, TR/EN, "başlangıç şablonu" uyarılı — gerçek hukuki inceleme hâlâ gerekli), register sayfasına onay satırı.
   - nginx: `infra/nginx/nginx.conf`'a `/api/v1/` prefix-korumalı location bloğu (çift `/api/api/v1` sorunu) + WebSocket `Upgrade`/`Connection` header'ları (`/ws/feed` artık prod'da çalışacak).
   - `frontend/lib/api.ts`'te `BASE` export edildi, 3 dosyadaki (`account`, `dashboard`, landing footer) hardcoded `localhost:8000` linkleri düzeltildi.
   - Landing sayfasına kayıt gerektirmeyen canlı semantik arama demosu (`LandingSearchDemo.tsx`, `/news/search` public endpoint'i kullanır, `searchNewsPublic()`).
   - **Hâlâ eksik (bu turda kapsam dışı bırakıldı):** hesap silme endpoint'i yok (privacy sayfasında açıkça belirtildi), analytics/hata takibi yok, kişiselleştirme (onboarding wizard, entity-aware alert UI) — bkz. "Kişiselleştirme paketi" sonraki adım.

### Kasıtlı Kapsam Dışı (fayda/maliyet uygun değil)
K8s/Helm, Qdrant migration, CQRS, NTV Playwright scraper, Twitter/X entegrasyonu, custom (Stripe dışı) billing portalı

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
- **i18n/dil dallanması:** `if language == "TR" else "..."` gibi if/else zincirleri YASAK (SOLID Open/Closed ihlali — yeni dil eklemek her seferinde koda dokunmayı gerektirir). Bunun yerine sözlük tabanlı lookup kullan: `_STRINGS: dict[str, dict[str, str]]` + `_t(language, key)` (bkz. `email_adapter.py`, frontend'de zaten `lib/i18n.ts::UI[lang]`). Yeni dil = yeni bir dict bloğu, mevcut fonksiyonlara dokunulmaz. Bu sadece dil için değil, "duruma göre metin/davranış seç" ihtiyacı olan HER yeni kod için varsayılan yaklaşım.

---

## ÇALIŞMA KOMUTLARI

```powershell
# Test
venv\Scripts\python.exe -m pytest tests/ -v

# Belirli test dosyası
venv\Scripts\python.exe -m pytest tests/adapters/test_groq_analyzer.py -v

# Frontend (Node v24 host'ta kurulu — PATH yenilenmediyse tam yol gerekebilir)
cd frontend; npm install        # ilk kez / bağımlılık değiştiyse
cd frontend; npm run dev        # http://localhost:3000 (hot reload)
cd frontend; npm run build      # tip kontrolü + prod build doğrulama (DEĞİŞİKLİK SONRASI ÇALIŞTIR)

# Temiz aç/kapa (v1.18'de Redpanda'ya geçildi — tek container, iki-katmanlı
# zookeeper→kafka başlangıç bağımlılığı kalktı, ama yine de temiz aç/kapa iyi pratik)
docker compose down
docker compose up -d

# Docker — kod değiştiyse (volume mount sayesinde build GEREKMEZ)
docker-compose restart worker
docker-compose restart app
docker-compose restart frontend

# Docker — ilk çalıştırma veya requirements/Dockerfile değiştiyse (SADECE bu durumda build)
docker-compose up --build -d

# Docker — sıfırdan (DB + ChromaDB silinir)
docker-compose down -v && docker-compose up --build -d

# Docker — gereksiz image/cache temizliği (buildx cache'i builder prune TEMİZLEMEZ, ayrı komut şart)
docker builder prune -f && docker buildx prune -af && docker volume prune -f

# Loglar
docker logs nexstream_worker --tail 30
docker logs nexstream_chromadb --tail 20
```

**Operasyonel notlar:** `docker compose up -d` ilk çalıştırmada bazen "kafka is unhealthy" diyip çıkabilir — kafka aslında sağlıklıdır, komutu tekrar çalıştırmak yeterli (tek seferlik healthcheck zamanlama yarışı). App container restart sonrası SentenceTransformer modeli sıfırdan yüklendiği için `/health` 200 dönene kadar ~1-2 dakika sürer; canlı test yapıyorsan tek istekle değil polling ile bekle.

**⚠️ `npm run build`'i frontend container ÇALIŞIRKEN host'ta ÇALIŞTIRMA (21 Temmuz 2026'da tekrar yaşandı):** `docker-compose.yml` frontend'i `.:/app` volume ile mount ediyor ve container içinde `npm run dev` koşuyor. Host'ta `npm run build` çalıştırmak paylaşılan `.next` klasörünü PROD çıktısıyla eziyor → dev server'ın beklediği chunk dosyaları kaybolur, sayfa HTML 200 döner ama TÜM CSS/JS 404 verir; kullanıcı "site bembeyaz, sadece HTML var, hiç renk yok" olarak görür. **Kurtarma:** `docker compose stop frontend` → `rm -rf frontend/.next` → `docker compose start frontend` (dev server `.next`'i sıfırdan üretir) → tarayıcıda Ctrl+Shift+R. Tip kontrolü gerekiyorsa ya önce container'ı durdur ya da `npx tsc --noEmit` kullan (`.next`'e dokunmaz).

**Docker build — pip hash hatası ve 85 dakikalık build (21 Temmuz 2026'da çözüldü):** `Dockerfile`/`Dockerfile.light`'ta eskiden `pip install --no-cache-dir` vardı; torch/transformers dahil GB'larca paket HER build'de sıfırdan iniyordu (~85 dk) ve inen byte arttıkça rastgele bozulma `ERROR: THESE PACKAGES DO NOT MATCH THE HASHES FROM THE REQUIREMENTS FILE` olarak patlıyordu (her denemede FARKLI pakette — bu paket sorunu değil, indirme bozulmasıdır; `requirements.txt`'te zaten hash yok). Çözüm: BuildKit cache mount + retry — `RUN --mount=type=cache,target=/root/.cache/pip pip install --retries 10 --timeout 120 -r requirements.txt`. Wheel'ler image katmanına girmez (boyut artmaz) ama build'ler arasında saklanır, retry'lar yeniden indirmez. **`--no-cache` ile tam temiz build denemek bu durumda ÇÖZÜM DEĞİL, sorunu büyütür** (her şeyi tekrar indirtir).

**Telefondan/başka cihazdan (aynı hotspot/LAN) erişim (8 Temmuz 2026'da denendi, geri alındı — yöntem burada kayıtlı):**
1. Bilgisayarın o anki LAN IP'sini bul: PowerShell'de `Get-NetIPAddress -AddressFamily IPv4` (hotspot'a bağlıysa genelde `Wi-Fi` arayüzü, `172.20.10.x` gibi bir IP — Dhcp kaynaklı).
2. `.env`'e GEÇİCİ olarak ekle: `NEXT_PUBLIC_API_URL=http://<IP>:8000` ve `CORS_ORIGINS=http://localhost:3000,http://localhost:8000,http://<IP>:3000` (`docker-compose.yml`'de bu iki değişken zaten `${VAR:-default}` deseniyle override edilebilir halde).
3. `docker compose up -d app frontend` (sadece `restart` yetmez, env yeniden okunmaz).
4. Windows'un ağ profili "Public" ise (hotspot genelde öyle sınıflandırılır) gelen bağlantılar varsayılan engelli — yönetici PowerShell'de `New-NetFirewallRule -DisplayName "..." -Direction Inbound -Protocol TCP -LocalPort 3000,8000 -Action Allow -Profile Public` gerekir (ben admin yetkisi olmadığı için bunu SADECE kullanıcı çalıştırabilir).
5. **İş bitince mutlaka geri al:** `.env`'deki iki satırı sil (IP değişince/farklı ağda unutulursa localhost dev'i sessizce bozar) + `docker compose up -d app frontend` ile sıfırla + `Remove-NetFirewallRule -DisplayName "..."` (Public profildeki KALICI bir güvenlik açığı, sadece o oturum için açılmalı).

---

## BİLİNEN NOTLAR

- Groq free tier: 14.400 req/gün — production'da dikkat
- Scraper limit: 25 haber/kaynak/çalışma
- DB duplicate kontrolü var — aynı URL tekrar kaydedilmez
- ChromaDB 1.5.5 kurulu (0.5.23 uvicorn conflict veriyordu)
- `docker-compose down -v` sonrası ChromaDB da sıfırlanır
- Dashboard sidebar kaldırıldı, tüm kontroller üst bar'da
- README UTF-8 BOM'suz olarak yeniden yazıldı (önceki versiyon UTF-16 idi, GitHub'da bozuk görünüyordu)
- `prometheus-fastapi-instrumentator` app'e eklendi, `/metrics` endpoint Prometheus format döndürür
- `docker-compose.prod.yml` production için, `docker-compose.yml` dev için kullanılır
- `infra/nginx/nginx.dev.conf` SSL olmadan local test için (nginx.conf SSL gerektirir)
- Worker sıralı işleme: `asyncio.create_task` → `await` + 2sn throttle, Groq rate limit patlamasını önler
- **v1.8 kaynaklar:** Guardian Tech / The Verge WebFetch ile doğrulanamadı (Claude Code domain kısıtı) ama bilinen kararlı beslemeler; TechCrunch/Hacker News/AA doğrulandı. Ölü besleme worker'ı çökertmez (scraper exception'ı yutar, [] döner)
- **v1.8 cloud fallback:** `HUGGINGFACE_API_KEY` boşsa fallback devre dışı (sadece Groq çalışır), davranış v1.7 ile aynı. Analyzer artık `factory.build_analyzer()` ile kurulur, `GroqAnalyzer()` doğrudan çağrılmaz. Concrete analyzer'lar `analyze_or_raise` ile `AnalysisError` fırlatır; `FallbackAnalyzer.analyze_text` asla fırlatmaz (nötr fallback)
- **v1.8 related:** ilişki grafı ayrı tablo değil, on-the-fly entity overlap (son 500 entity'li haber taranır). `entities` SQL NULL filtresi postgres'te çalışır; SQLite/ORM'de None → JSON 'null' saklanır (servis boş entity'yi zaten güvenle eler)
- **v1.8 skorlama:** `quality_score` + `credibility_score` + `corroboration_count` ingest'te `service._enrich_metadata` ile set edilir; saf hesap `domain/scoring/`'de. Eski haberler için migration sonrası `POST /news/reanalyze` quality'yi doldurur (credibility/corroboration ingest-only)
- **v1.8 migration:** prod'da `migrations/v1_8_quality_credibility.sql` çalıştırılmalı (dev'de `create_all` otomatik ekler)
- **v1.9 migration:** prod'da `migrations/v1_9_users_sessions_usage_sponsor.sql` çalıştırılmalı (users, user_sessions, usage_logs, sponsors tabloları)
- **v1.9 yeni env var'lar:** `SESSION_TTL_DAYS` (30), `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`, `STRIPE_PRO_PRICE_ID`, `STRIPE_ENTERPRISE_PRICE_ID`, `REDIS_URL` (boşsa NullCache)
- **v1.9 auth (v1.12 öncesinde cookie'ye taşındı — madde 6):** kimlik artık birincil olarak HttpOnly `nxs_session` cookie'si; `X-Session-Token` header sadece SSR/test fallback'i. bcrypt direkt kullanılıyor (passlib yerine — bcrypt 5.x ile uyumsuz)
- **Dev'de session cookie gotcha:** `session_cookie_secure` varsayılanı `True` (prod için doğru) — `docker-compose.yml`'e `SESSION_COOKIE_SECURE=false` eklenmezse cookie sadece HTTPS'te gönderilir, local HTTP dev'de login 200 döner ama cookie tarayıcıya hiç gitmez (sessiz kırılma). Zaten dev compose'a eklendi; yeni bir compose varyantı oluşturursan unutma.
- **Tailwind responsive class + inline style çakışması:** Proje çoğunlukla inline `style` objesi kullanıyor ama Tailwind da kurulu (`globals.css`'te `@tailwind base/components/utilities`, breakpoint'ler varsayılan). `hidden md:flex` gibi responsive display class'ları kullanılan bir elementin inline style'ına ASLA `display` ekleme — inline style her zaman class'ı ezer, `md:hidden` hiç çalışmamış gibi görünür (Navbar mobil menüsünde tam bu yüzden panel masaüstünde açık kalıyordu). Açık/kapalı state tutan mobil panellerde ayrıca `matchMedia("(min-width: 768px)")` ile ekran büyüyünce state'i otomatik kapatan bir effect ekle — yoksa görünmez `position:fixed;inset:0` backdrop'u state açık kaldığı sürece tıklamaları yutmaya devam eder.
- **v1.9 tier:** `check_tier_limit` dependency v1 router'da, Free=100/gün, Pro=2000/gün, Enterprise=sınırsız
- **v1.9 usage log:** `/api/v1/` endpointleri için asyncio background task ile loglanır
- **v1.9 admin:** `/admin/usage` + `/admin/sponsors` CRUD — `X-API-Key` gerektirir
- **v1.9 billing:** Stripe yapılandırılmazsa `/billing/*` → 503. Webhook `stripe-signature` header doğrulaması yapılır
- **v1.10 frontend tema:** Tema sistemi `frontend/lib/theme/registry.ts`'te tek doğruluk noktası. Renk token'ları `globals.css`'te `[data-theme="<id>"]` blokları (`--accent`, `--accent-soft`, `--accent-line`, `--glow`, `--font-display` vb.). Inline stillerde sabit renk KULLANMA — token kullan, yoksa tema değişince uyumsuz kalır. Efektler saf Canvas, `useCanvasScene` hook'unu paylaşır.
- **v1.10 i18n:** TÜM kullanıcıya görünen string `lib/i18n.ts`'te (UI + FEATURES/PRICING/TIER_DETAILS). Sayfaya hardcoded TR metin YAZMA — yoksa EN'e geçince çevrilmez (eski bug buydu). `THEME_LIST`'teki `labelKey`/`tagKey`, `UI[lang]` içinden okunur.
- **v1.10 trending:** API alanı `name` (eskiden frontend yanlışlıkla `entity` bekliyordu → boş isim, sadece sayı görünüyordu). `TrendingEntity` = `{name, count, type?, example_titles?}`. Pill'e tıklayınca `/dashboard/search?q=...`'a gider; search sayfası mount'ta `window.location.search`'ten `q`'yu okur (useSearchParams Suspense gerektirmesin diye).
- **v1.10 kafka dayanıklılığı:** compose'da kafka/zookeeper/chromadb'ye `restart: unless-stopped` eklendi (eskiden yoktu → çökünce kalkmıyordu, "NodeExists"/stale state buradan). kafka'ya `stop_grace_period: 30s`. `KafkaPublisherAdapter.start()` artık retry'lı (başarısız her denemede producer'ı yeniden yaratır) → app kafka geç açılırsa çökmez. **Temiz aç/kapa:** `docker compose down` sonra `docker compose up -d`. Parçalı/ani kapanış stale broker bırakabilir ama restart politikası kendini düzeltir.
- **v1.10 billing/admin işleyişi:** "Admin API Anahtarı" tek paylaşımlı sır (`API_KEY` env, default `dev-key-change-me`) — kullanıcı-başına DEĞİL. Admin sayfaları (/admin/usage, /admin/sponsors) bu key ile çalışır. Pro/Kurumsal butonu Stripe yapılandırılmadığı için 503 verir (gerçek Stripe hesabı + `STRIPE_*` env gerekir) — lokal dev'de beklenen davranış. Landing CTA'ları artık auth-aware (giriş yapmışsa /dashboard veya /account).
- **v1.10 node lokal:** Node v24 + npm host'ta (`C:\Program Files\nodejs`). Frontend lokalde `cd frontend; npm run build` ile derlenir. Docker `Dockerfile.dev` `npm run dev` (SWC) tam tip kontrolü YAPMAZ → tip hataları sadece `next build`'te görünür. Frontend değişiminden sonra `npm run build` ile doğrula.
- **v1.11 env var'lar:** `BILLING_DEV_MODE` (false — true iken checkout Stripe'sız tier yükseltir, PROD'DA AÇMA), `ADMIN_EMAILS` (boş — virgülle ayrılmış liste, eşleşen kullanıcı DB yazılmadan admin sayılır)
- **v1.11 admin yetkisi (v1.13'te rol hiyerarşisine genişledi, bkz. MEVCUT DURUM):** `require_admin` (auth_utils) iki yol kabul eder: X-API-Key (makine) veya `role="admin"` kullanıcı oturumu. `require_moderator` aynı mantıkla moderator+admin'i kabul eder (görüntüleme). Yetkisiz kullanıcıya 403, anonime 401. `/auth/me` artık `role` + `is_moderator` + (geriye uyumlu) `is_admin` döner; frontend Navbar/hesap admin linklerini `is_moderator`'a göre gösterir. Admin sayfaları moderator+ oturumla otomatik yüklenir, rol değiştirme sadece admin'e açık.
- **v1.11 kullanıcı API key:** `nxs_` önekli, `/account/api-key` ile yönetilir, `X-User-Key` header'ı ile `/api/v1`'de kullanılır. Session ile key aynı anda gelirse session kazanır. Key düz saklanır (session token'lar gibi) — bilinçli sadelik tercihi.
- **v1.11 billing testleri:** `billing_router.settings` MagicMock ile patch'lenen testlerde `ms.billing_dev_mode = False` set edilmeli — yoksa truthy MagicMock dev-mode yolunu tetikler.
- **v1.11 refactoring:** `adapters/api/controller.py` silindi (main.py ile çakışan ölü legacy). `news_orm.py` sadece geriye-uyum köprüsü (orm_models'tan re-export). Tüm src/ modüllerinde docstring var; yeni modül eklerken docstring zorunlu kabul et. Frontend auth-context açılışta `/auth/me` ile kullanıcıyı tazeler (401'de oturumu düşürür).
- **Prod deploy öncesi kontrol listesi:** `docker-compose.prod.yml`'de `FRONTEND_URL` env var'ı gerçek domain ile set edilmeli (boş kalırsa `settings.py`'deki `http://localhost:3000` default'u kullanılır, şifre sıfırlama maili yanlış linke gider). `RESEND_API_KEY`/`EMAIL_FROM` de dolu olmalı, yoksa mail sessizce `ConsoleEmailAdapter`'a düşer (log-only). **v1.17 güvenlik denetimi sonrası ZORUNLU olanlar:** `ENVIRONMENT=production` (prod compose zaten set eder), `API_KEY` (gerçek rastgele — `openssl rand -hex 32`), `CORS_ORIGINS` (gerçek domain, `*` DEĞİL), `GRAFANA_PASSWORD` (compose `:?` ile zorunlu kılar, yoksa deploy durur), `SESSION_COOKIE_SECURE=true`. İlk dördü zayıf/eksikse uygulama açılışta `_reject_unsafe_production_config` ile ölür — sessizce güvensiz çalışmaz, bu KASITLI.
- **v1.17 güvenlik notları (kalıcı kurallar):** (1) `.env`'i git'ten kaldırmak sızıntıyı ÇÖZMEZ — blob geçmişte kalır (`git show <commit>:.env` çalışır), tek çözüm sızan secret'ı rotate etmektir. (2) Yeni bir rate-limitli endpoint yazarken `@limiter.limit` decorator'ı fonksiyona `request: Request` parametresi ZORUNLU kılar; handler'ı testte doğrudan çağıran mevcut testler varsa (`test_health_router.py` deseni) sahte bir `Request` scope'u geçmeleri gerekir. (3) slowapi limiter state'i TÜM test session'ı boyunca paylaşılır (conftest `src.main`'i reload eder ama limiter singleton'ını etmez) — bir endpoint'e N test yazacaksan dakikalık limitin N'den büyük olduğundan emin ol. (4) E-posta/HTML üreten her yeni kodda dış kaynaklı veri (haber başlığı/özeti, sponsor alanları) `html.escape()`'ten geçmeli.
- **v1.17 yeni env var:** `ENVIRONMENT` (varsayılan `"development"`; `"production"` yapılınca güvenlik guard'ı devreye girer — sadece prod compose set eder).
- **nginx bilinen boşluklar (v2.0'a bırakıldı, henüz düzeltilmedi):** `location /api/` bloğu `/api/` prefix'ini sıyırıp app'e iletiyor; ama `/api/v1` router'ının kendi route'ları zaten `/api/v1/...` ile başlıyor, yani dışarıdan doğru erişim `/api/api/v1/...` olur — çirkin ama çalışır, düzeltilmedi. Ayrıca `/api/` location bloğunda WebSocket `Upgrade`/`Connection` header'ları yok, yani `/ws/feed` canlı akışı prod'da nginx arkasında şu an çalışmaz (dev'de nginx yok, doğrudan 8000'e gidildiği için sorun çıkmıyor).
- **v1.12 öncesi durum taraması (bu session'da yapıldı):** Responsive/erişilebilirlik/SEO/tema-performans-profili maddelerinin hiçbiri henüz başlamadı; sadece dashboard sayfasında kısmi bir skeleton-loading deseni var (diğer sayfalarla tutarsız). Yeni bir session bu maddelere başlarken sıfırdan tasarlamalı.
- **v1.11 sonrası yeni env var'lar:** `FRONTEND_URL` (boş — prod'da gerçek domain ile set edilmeli, şifre sıfırlama linki için), `PASSWORD_RESET_TTL_MINUTES` (60), `SEARCH_RECENCY_DECAY_FLOOR` (0.5), `SEARCH_RECENCY_WINDOW_DAYS` (30), `CHROMA_RETENTION_DAYS` (90 — 0 kapatır), `DB_RETENTION_DAYS` (0 — kapalı, açarsan Postgres'ten KALICI siler), `RETENTION_HOUR_UTC` (4), `EMAIL_VERIFICATION_TTL_MINUTES` (1440 — v1.15, e-posta doğrulama linki geçerlilik süresi), `EXPORT_MAX_ROWS` (20000 — v1.16, ham veri export üst satır sınırı), `WS_MAX_CONNECTIONS_PER_USER` (5 — v1.18, `/ws/feed` per-user tavan), `WS_MAX_TOTAL_CONNECTIONS` (500 — v1.18, `/ws/feed` global tavan).
- **Resend sandbox kısıtı (v1.15'te bulundu, TÜM ResendEmailAdapter gönderimlerini etkiler):** `resend.com/domains`'te doğrulanmış bir domain yoksa, `RESEND_API_KEY` gerçek/prod modda bile olsa sadece hesap sahibinin KENDİ e-postasına mail gönderilebilir — başka adrese denemek 403 ile patlar (sessizce loglanır, akışı bozmaz). Prod'a domain doğrulaması yapılmadan çıkılırsa hesap sahibi dışındaki gerçek kullanıcılar hiç mail almaz.
- **Ders — sessiz veri kaybı deseni:** `save_article()`'daki id-propagation bug'ı aylarca fark edilmeden ChromaDB indexlemeyi sessizce devre dışı bırakmıştı (exception fırlatmıyordu, sadece `article.id` None kalıyordu ve çağıran kod bunu es geçiyordu). Yeni bir "kaydet → sonra ID'ye ihtiyaç duyan bir şey yap" akışı eklerken, ORM nesnesinin PK'sının domain nesnesine gerçekten geri yazıldığını (`refresh()` + atama) doğrula — `user_repository.py::create_user` doğru pattern.
