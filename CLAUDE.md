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
│   │   └── scheduler_service.py   # 10dk'da bir Kafka'ya mesaj atar
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
└── v1_11_admin_api_keys.sql       # v1.11 (users.is_admin, users.api_key + unique index)
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
| zookeeper | — (internal) | Kafka koordinatör |
| kafka | — (internal) | Mesaj kuyruğu |
| worker | — | Kafka consumer + Groq analyzer |
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
| zookeeper | — (internal) | Kafka koordinatör |
| kafka | — (internal) | Mesaj kuyruğu |
| worker | — (internal) | Kafka consumer + Groq analyzer |
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

- **Versiyon:** v1.11.0 ✅ Monetizasyon & Erişim (billing dev-mode, rol tabanlı admin, self-service kullanım paneli, kullanıcı başına API key) + proje geneli clean-code refactoring (tüm modüllerde docstring, ölü kod temizliği)
- **v1.11 sonrası ek (henüz versiyonlanmadı):** Şifremi unuttum / şifre sıfırlama mekanizması — `POST /auth/forgot-password` + `POST /auth/reset-password`, `password_reset_tokens` tablosu (`migrations/v1_12_password_reset_tokens.sql`), `EmailPort.send_password_reset` (Console + Resend), şifre değişince tüm oturumlar düşürülür
- **Test sayısı:** 380 test, hepsi yeşil (backend); frontend `npm run build` temiz
- **Frontend:** Next.js 14 + React. Streamlit dashboard tamamen kaldırıldı (`dashboard/app.py` silindi, compose'dan çıktı). 9 sinematik tema, tam TR/EN i18n. Port **3000**.
- **Haber kaynağı:** 17 (11 → 17, +Anadolu Ajansı, AA Ekonomi, Guardian Tech, TechCrunch, Hacker News, The Verge)
- **CI/CD:** GitHub Actions — push/PR on main, postgres:15 service, `python -m pytest`
- **Branch:** main (tüm özellikler merge edildi)
- **Hedef:** CV/portfolio projesi → canlı ürüne geçiş (ücretsiz başla, gelir varsa harca)
- **Kısıt:** VPS'te 7/24 bağımsız çalışacak, local bağımlılık yok
- **Lokal araçlar:** Node.js v24 + npm host'a kuruldu (winget). Docker Desktop, PostgreSQL 17, Git zaten kurulu.

---

## TAMAMLANAN ÖZELLİKLER (v1.2.0)

### Hybrid Search
- `POST /news/search`: ChromaDB (semantic) + PostgreSQL (keyword) birleşik
- Coverage-based skor, normalize embedding, `1/(1+distance)` formülü

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

**Tamamlananlar:** v1.2 → v1.11 (detaylar yukarıdaki milestone'larda). v1.11 sonu: 373 test, lokalde TAM çalışır (billing dahil — `BILLING_DEV_MODE=true` ile Stripe'sız demo). Gerçek Stripe entegrasyonu kod tarafında hazır; sadece gerçek hesap + `STRIPE_*` anahtarları + `stripe listen` webhook'u gerekir (v2.0 deploy işi).

### v1.12 — UX, Erişilebilirlik & SEO Cilası (frontend ağırlıklı)
1. **Responsive geçiş** — tüm sayfalar mobil/tablet; Navbar tema seçici + admin tabloları dar ekranda.
2. **Erişilebilirlik** — focus halkaları, aria etiketleri, klavye navigasyonu, kontrast (özellikle koyu temalar).
3. **SEO** — sayfa-başına OpenGraph/Twitter meta, JSON-LD, `sitemap.xml` + `robots.txt`, Next.js metadata API.
4. **Tema ince ayarı** — efekt yoğunluğu/performans profilleri (low/high), istenirse 1-2 yeni tema.
5. **Durum cilası** — tutarlı skeleton + boş/hata state'leri.

### v2.0 — Public Launch (v1.12 sonrası)
1. **Domain & VPS** — `nexstream.news`, Hetzner CX22, `docker-compose.prod.yml` ile deploy, Cloudflare CDN, UptimeRobot.
2. **API dökümantasyon portalı** — Swagger/Redoc cila, demo API key, kullanım örnekleri, Postman collection.
3. **Launch içeriği** — landing son metinler, OG görselleri, Product Hunt materyali.
4. **README** — ✅ v1.10'da tüm proje geneli güncellendi (gerekirse Mermaid diyagram + GIF demo eklenir).

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

# Temiz aç/kapa (stale kafka/zookeeper sorununu önler)
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
- **v1.9 auth:** `X-Session-Token` header ile session tabanlı auth. bcrypt direkt kullanılıyor (passlib yerine — bcrypt 5.x ile uyumsuz)
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
- **v1.11 admin yetkisi:** `require_admin` (auth_utils) iki yol kabul eder: X-API-Key (makine) veya admin kullanıcı oturumu. Yetkisiz kullanıcıya 403, anonime 401. `/auth/me` artık `is_admin` döner; frontend Navbar/hesap admin linklerini buna göre gizler. Admin sayfaları admin oturumuyla otomatik yüklenir.
- **v1.11 kullanıcı API key:** `nxs_` önekli, `/account/api-key` ile yönetilir, `X-User-Key` header'ı ile `/api/v1`'de kullanılır. Session ile key aynı anda gelirse session kazanır. Key düz saklanır (session token'lar gibi) — bilinçli sadelik tercihi.
- **v1.11 billing testleri:** `billing_router.settings` MagicMock ile patch'lenen testlerde `ms.billing_dev_mode = False` set edilmeli — yoksa truthy MagicMock dev-mode yolunu tetikler.
- **v1.11 refactoring:** `adapters/api/controller.py` silindi (main.py ile çakışan ölü legacy). `news_orm.py` sadece geriye-uyum köprüsü (orm_models'tan re-export). Tüm src/ modüllerinde docstring var; yeni modül eklerken docstring zorunlu kabul et. Frontend auth-context açılışta `/auth/me` ile kullanıcıyı tazeler (401'de oturumu düşürür).
- **Prod deploy öncesi kontrol listesi:** `docker-compose.prod.yml`'de `FRONTEND_URL` env var'ı gerçek domain ile set edilmeli (boş kalırsa `settings.py`'deki `http://localhost:3000` default'u kullanılır, şifre sıfırlama maili yanlış linke gider). `RESEND_API_KEY`/`EMAIL_FROM` de dolu olmalı, yoksa mail sessizce `ConsoleEmailAdapter`'a düşer (log-only).
- **nginx bilinen boşluklar (v2.0'a bırakıldı, henüz düzeltilmedi):** `location /api/` bloğu `/api/` prefix'ini sıyırıp app'e iletiyor; ama `/api/v1` router'ının kendi route'ları zaten `/api/v1/...` ile başlıyor, yani dışarıdan doğru erişim `/api/api/v1/...` olur — çirkin ama çalışır, düzeltilmedi. Ayrıca `/api/` location bloğunda WebSocket `Upgrade`/`Connection` header'ları yok, yani `/ws/feed` canlı akışı prod'da nginx arkasında şu an çalışmaz (dev'de nginx yok, doğrudan 8000'e gidildiği için sorun çıkmıyor).
- **v1.12 öncesi durum taraması (bu session'da yapıldı):** Responsive/erişilebilirlik/SEO/tema-performans-profili maddelerinin hiçbiri henüz başlamadı; sadece dashboard sayfasında kısmi bir skeleton-loading deseni var (diğer sayfalarla tutarsız). Yeni bir session bu maddelere başlarken sıfırdan tasarlamalı.
