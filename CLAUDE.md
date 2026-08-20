# NexStream News Engine — CLAUDE.md

Bu dosya Claude Code için proje bağlamını sağlar — GÜNCEL/canlı referans (mimari,
kararlar, durum, kurallar, komutlar, kalıcı gotcha'lar). Her session başında oku,
sonra gerekli dosyaları kendin aç.

**Kronolojik geliştirme tarihçesi (hangi sürümde ne yapıldı, hangi bug nasıl
bulunup düzeltildi) `docs/CHANGELOG.md`'de** — 18 Ağustos 2026'da bu dosya ~700
satıra ulaşınca oraya ayrıştırıldı, session başında okunması gerekmez, sadece
"bu neden böyle yapılmış" sorusuna cevap ararken aç.

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
│   │   ├── embedding_port.py      # class EmbeddingPort (ABC)
│   │   └── query_expansion_port.py # class QueryExpansionPort (ABC) — sorgu genişletme (v2.3)
│   ├── schemas/
│   │   └── news_schema.py         # Pydantic: NewsResponse, SearchRequest, SearchResult, TrendingResponse, RelatedResponse
│   └── scoring/                   # Saf domain skorlama (v1.8) — dış bağımlılık yok
│       ├── quality.py             # compute_quality_score — uzunluk/entity/summary/başlık
│       └── credibility.py         # SOURCE_CREDIBILITY seed + compute_credibility
├── application/
│   └── services/news_service.py   # Orchestration — port'ları bağlar, get_related, _enrich_metadata dahil
├── adapters/
│   ├── analysis/
│   │   ├── groq_analyzer.py       # Groq openai/gpt-oss-20b — birincil analyzer (v1.5+, model v2.1.1'de değişti)
│   │   ├── huggingface_analyzer.py # HF Inference API — opsiyonel yedek (v1.8)
│   │   ├── fallback_analyzer.py   # Groq dene, başarısızsa HF, hepsi olmazsa nötr (v1.8)
│   │   ├── common.py              # Paylaşılan prompt + JSON parse + nötr fallback (v1.8)
│   │   ├── groq_query_expander.py # Groq ile ilişkili terim üretir ("İstanbul"→"Beykoz"), fail-open (v2.3)
│   │   ├── caching_query_expander.py # QueryExpansionPort'u CachePort ile saran decorator (v2.3)
│   │   └── factory.py             # build_analyzer() + build_query_expander() — kompozisyon noktası (v1.8)
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
│   │   ├── sentence_transformer_embedder.py  # SentenceTransformerEmbedder (singleton) — SADECE embedder image'ında
│   │   ├── http_embedder.py                  # HttpEmbedderAdapter — embedding'i embedder servisine devreder (v2.0)
│   │   ├── embedder_factory.py               # build_embedder() — kompozisyon noktası (v2.0)
│   │   ├── embedder_service.py               # Modeli tek kopya yükleyen mini FastAPI app (v2.0)
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
│           ├── account_router.py # /account: usage paneli + kişisel API key (v1.11) + saved (v2.2)
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
├── v1_12_password_reset_tokens.sql # şifre sıfırlama (password_reset_tokens tablosu)
└── v2_2_saved_articles.sql        # v2.2 (saved_articles — kaydet/sonra oku)
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
| embedder | — (internal) | SentenceTransformer modelini TEK kopya tutan servis (v2.0) — app/worker ona HTTP ile sorar |
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
| embedder | — (internal) | SentenceTransformer modelini TEK kopya tutan servis (v2.0) — app/worker ona HTTP ile sorar |
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

**Neden Groq?** Gemini'den taşındı. 14.400 req/gün ücretsiz, requests kütüphanesi yeterli (SDK yok). Rate limit: `Retry-After` header kullanılıyor. v1.5'ten itibaren tek prompt'ta sentiment + entities + topic çıkarılıyor. **Model: `openai/gpt-oss-20b`** (18 Ağu 2026'da `llama-3.1-8b-instant`'tan değişti — Groq o modeli tamamen kaldırdı, bkz. "v2.1.1" bloğu aşağıda). `reasoning_effort="low"` + `max_tokens=600` (reasoning modeli, `message.reasoning` alanı `content`'ten ayrı döner — JSON parse'ı bozmuyor). **Groq'un model listesi zamanla değişiyor/modeller kaldırılıyor** — `GET https://api.groq.com/openai/v1/models` ile periyodik kontrol faydalı; 404 + `model_not_found` görürsen model kaldırılmış demektir (rate limit/kota DEĞİL).

**Neden sentence-transformers?** Groq'un embedding API'si yok. `paraphrase-multilingual-MiniLM-L12-v2` modeli TR+EN destekler, tamamen local çalışır, API key gerektirmez. Kurulu versiyon: 3.3.1, torch: 2.10.0 (CPU wheel).

**Neden ayrı bir `embedder` servisi? (v2.0)** `app` ve `worker` modeli AYRI AYRI RAM'e yüklüyordu — t3.small'ın (1.9GB) kaldıramayacağı ~600MB'lık israf. Model artık tek bir serviste duruyor, ikisi de `HttpEmbedderAdapter` ile HTTP'den soruyor. **Domain katmanı hiç değişmedi** — mevcut `EmbeddingPort` soyutlaması aynen kullanıldı, hexagonal mimarinin karşılığını verdiği yer tam olarak burası. Yan kazanç: `app`/`worker` image'larında torch YOK (1.55GB → 516MB) ve `app` 1-2 dakika yerine ~6 saniyede healthy oluyor.

**Neden `chromadb-client`? (v2.0)** Kod yalnızca `chromadb.HttpClient` kullanıyor ama tam sunucu paketi kuruluydu (onnxruntime, tokenizers, opentelemetry, kubernetes client...). Kurulu versiyon: `chromadb-client` 1.5.5; sunucu imajı `chromadb/chroma:1.5.9` (= chroma sunucu 1.4.4). **DİKKAT:** imaj etiket numarası sunucu sürümünü YANSITMIYOR — `:1.5.5` etiketi daha ESKİ bir sunucu (1.4.1). Pin ederken `chroma --version` çıktısına bak.

**Neden ChromaDB?** Local, ücretsiz, Docker'a kolay eklenir, persistent storage destekler. `IS_PERSISTENT=TRUE` env var ile volume'a yazar.

**Neden hexagonal?** Kurs projesi — kurumsal mimari dersi için. Separation of concerns önemli. Yeni adapter eklemek domain'i bozmaz.

**Database URL:** `DATABASE_URL` env var yok. Ayrı `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD`, `DB_NAME` kullanılır. `src/infrastructure/config/database.py`'a bak.

**TextBlob:** Tamamen kaldırıldı. Groq ile değiştirildi. Hiçbir yerde TextBlob kullanma.

---

## MEVCUT DURUM

- **Versiyon:** v2.2 🚀 **CANLIDA: https://nexstreamnewsengine.duckdns.org** (son deploy: 19 Ağustos 2026, commit `08b864d` — AWS t3.small, gerçek Let's Encrypt, 16 servis, boru hattı uçtan uca çalışıyor; hesap silme + kaydet/sonra oku + corroboration rozeti + okuma süresi + tarayıcı-yerel TTS + kullanıcı banlama + story cluster hepsi canlıda SSM üzerinden uçtan uca test edildi — bkz. YOL HARİTASI madde 10/11/14). İlk canlıya çıkış: 29 Temmuz 2026.
- **Test sayısı:** 717 test, hepsi yeşil (backend, 20 Ağu 2026 — arama sorgu genişletme testleri dahil); frontend `tsc --noEmit` + `next build` temiz. Paket ~22 saniye sürüyor (29 Tem 2026'da 400sn'den düşürüldü — bkz. CHANGELOG "v2.0" bloğu).
- **Frontend:** Next.js 14 + React. 9 sinematik tema, tam TR/EN i18n, PWA (manifest + service worker). Port **3000**.
- **Mesaj kuyruğu:** Redpanda (Kafka wire-protokolü konuşan tek binary, `aiokafka` client kodu değişmedi).
- **Haber kaynağı:** 17 (TR: TRT Haber, BBC Türkçe, Hürriyet, Hürriyet Spor, Sabah, CNN Türk, Sözcü, Habertürk, HT Spor, Anadolu Ajansı, AA Ekonomi; EN: BBC Technology, BBC Sport, Guardian Tech, TechCrunch, Hacker News, The Verge).
- **CI/CD:** GitHub Actions — push/PR on main, postgres:15 service, `python -m pytest` + Dependabot (pip+npm+github-actions, haftalık) — 22 açık Dependabot PR'ı bekliyor (review/merge kararı kullanıcıda).
- **Branch:** `main` güncel. Prod deploy hâlâ `optimize/t3-small-ram`'dan yapılıyor — yeni işler için main'den kısa ömürlü feature branch aç, PR ile geri birleştir. Kirli bir working tree varken bile `git fetch && git switch -c <yeni-dal> origin/main` çalışır (uncommitted değişiklikleri yeni dala taşır) — dosyalar iki dal arasında çakışmıyorsa stash'e gerek yok. **19 Ağu 2026'da `optimize/t3-small-ram` main'e fast-forward edilip prod redeploy edildi** (`git push origin main:optimize/t3-small-ram` + SSM üzerinden `docker compose -f docker-compose.prod.yml up --build -d`) — ama main PR'larla ilerlemeye devam ettiği için tekrar birkaç commit ileride olabilir, redeploy öncesi `git log --oneline origin/main ^origin/optimize/t3-small-ram` ile fark kontrol et.
- **Hedef:** CV/portfolio projesi → canlı ürüne geçiş (ücretsiz başla, gelir varsa harca).
- **Kısıt:** VPS'te 7/24 bağımsız çalışıyor. **Bütçe: GERÇEKTEN $0/ay** (kalıcı kısıt) — AWS Free Plan'ın $100 kredisiyle karşılanıyor, ~$18,4'ü harcanmış (18 Ağu 2026), günlük yakım ~$0,93 (~$28/ay) → kredi mevcut hızla **Kasım 2026 ortasında** tükenir (28 Ocak 2027 son kullanma tarihinden ~2,5 ay önce) — bu tarihten önce bir karar gerekir (durdur, küçült, ya da tekrar Oracle Free dene).
- **Lokal araçlar:** Node.js v24 + npm host'a kuruldu (winget). Docker Desktop, PostgreSQL 17, Git zaten kurulu.

---

## YOL HARİTASI (kalan işler)

Tamamlanan işlerin tam kronolojik dökümü `docs/CHANGELOG.md`'de. Burada sadece
GERÇEKTEN bekleyen işler var:

1. **Anasayfa tasarım yenilemesi** — kullanıcı "şu an tamamen basit bir AI
   tasarımı gibi duruyor" dedi (18 Ağu 2026), özellikle hero. Bilinçli olarak
   BAŞLANMADI bu oturumda — gerçek bir tasarım kararı işi, `frontend-design`
   skill'i ile ayrı/temiz bir oturumda ele alınmalı, aceleye getirilmemeli.
2. **Gerçek Stripe entegrasyonu** — kod tarafı hazır; sadece gerçek hesap +
   `STRIPE_*` anahtarları + `stripe listen` webhook'u + `BILLING_DEV_MODE=false`
   gerekir. Türkiye'den hesap açılabiliyor mu belirsiz (kullanıcı kendi
   bilgileriyle denemeli) — kabul etmezse Iyzico/PayTR gibi bir alternatif
   kod tarafında sıfırdan yazım ister.
3. **Özel kaynak ekleme (custom source ingestion)** — kullanıcı kararıyla
   ŞİMDİLİK ertelendi, pricing metni "bize ulaşın" şeklinde yumuşatıldı
   (18 Ağu 2026). Tam private/per-user versiyonu gerçek bir mimari iş
   (kullanıcı bazlı veri izolasyonu şu an sistemde YOK) — ileride sadece
   talep eden kullanıcıya özel, elle açılan bir şey olarak düşünülebilir.
4. **Launch içeriği** — LinkedIn metni + OG görseli hazır (18 Ağu 2026).
   Kalan: Product Hunt materyali, varsa ek sosyal medya içeriği — düşük öncelik.
5. **Resend domain doğrulaması** — `resend.com/domains`'te doğrulanmış domain
   yoksa, hesap sahibi dışındaki kullanıcılara Resend üzerinden hiç mail gitmez
   (SMTP birincil olduğu için düşük öncelik — sadece SMTP düşerse Resend
   yedeğe geçer).
6. **Cloudflare proxy** — DNS şu an `nexstreamnewsengine.duckdns.org`'u
   doğrudan EC2 IP'sine çözüyor. DuckDNS subdomain'i Cloudflare'e
   delege/proxy edemezsin (Cloudflare bir zone'un TAMAMINA nameserver olmak
   ister, DuckDNS'in alt alan adı değil) — gerçek bir domain satın almak
   gerekiyor (~$10-15/yıl, tek seferlik). Kullanıcıya açıklandı, karar bekliyor.
7. **Dependabot PR'ları** — 19 Ağu 2026'da düşük riskli 12 tanesi merge edildi
   (GitHub Actions + Python/JS patch-minor bump'lar). Kalan 8 tanesi major
   bump (Next 14→16, TypeScript 5→7, Tailwind 3→4, React, Stripe SDK 7→15,
   feedgen 0.9→1.0) — gerçek test istiyor, review/merge kararı kullanıcıda.
8. ~~Hesap silme endpoint'i~~ — ✅ 19 Ağu 2026'da tamamlandı. `DELETE /account`
   (parola + checkbox onayı, owner rolü hariç, Stripe aboneliği varsa
   otomatik iptal, ilişkili tüm satırlar — sessions/token'lar/usage_log/
   bülten aboneliği — kalıcı silinir). Frontend'de /account sayfasında
   "Tehlikeli Bölge".
9. **Analytics/hata takibi** — yok (ör. Sentry, PostHog).
10. ~~Rakip taraması sonrası quick-win paketi~~ — ✅ 19 Ağu 2026'da tamamlandı
    (Ground News/Feedly/Inoreader/FreshRSS taraması, detay için scratchpad'deki
    araştırma raporuna bak). Kaydet/sonra oku (`/account/saved`, v2.2),
    kaynak "corroboration" rozeti (veri zaten vardı, sadece UI'a eklendi),
    tarayıcı-yerel TTS (Web Speech API).
    **19 Ağu 2026'da canlıya deploy edildi ve SSM üzerinden uçtan uca doğrulandı**
    (bkz. MEVCUT DURUM). Okuma süresi tahmini 20 Ağu 2026'da KALDIRILDI —
    bkz. madde 18.
18. **Gerçek makale metni scraping (okuma süresi için)** — 20 Ağu 2026'da
    okuma süresi rozeti kaldırıldı: hesap DB'de sakladığımız `content` alanına
    (RSS `<description>`/`<summary>`, ~30-80 kelimelik teaser) dayanıyordu,
    gerçek makale sitedeki tam metin hiç çekilmiyor — bu yüzden HER haber
    ~1dk çıkıyordu, yanıltıcıydı (kullanıcı bulgusu). Gerçek bir tahmin için
    17 kaynağın her birinin makale sayfasından tam metni çekmek (Readability/
    BeautifulSoup tarzı bir parser, `NTV Playwright scraper` kadar ağır değil
    ama yine de HTML yapısı kaynak başına farklı olduğu için kırılgan) ayrı
    bir roadmap maddesi — ingest anında mı yoksa on-demand mı çekileceği de
    ayrı bir karar (ingest anında tüm kaynaklar için ekstra HTTP + parse
    maliyeti, on-demand kart açıldığında gecikme).
11. ~~Story cluster görünümü~~ — ✅ 19 Ağu 2026'da tamamlandı. "Bu haberi kim
    nasıl anlatıyor" — `GET /news/{id}/sources` + `/api/v1/news/{id}/sources`
    (tier gating YOK, herkese açık — corroboration rozeti gibi şeffaflık
    özelliği). `ChromaSearchRepository.find_similar` zaten indexlenmiş
    embedding'i tekrar hesaplamadan (`collection.get`) benzerlik araması
    yapıyor, dedup eşiğinden (0.92) daha gevşek bir eşikle (0.72) aynı
    olayı farklı kaynakların anlattığı makaleleri yakalıyor. `NewsService.
    get_story_cluster` orkestrasyon, `NewsCard`'da kart footer'ında
    "🔗 Kaynaklar" toggle'ı.
12. **Web Push bildirimleri (breaking news)** — PWA service worker zaten
    kurulu; `web-push` + VAPID ile tamamen ücretsiz. Yeni bir
    `NotificationPort` adapter'ı gerektirir — tam "architectural" tur
    (spec + writing-plans). (19 Ağu 2026 rakip taraması, madde #6)
    **19 Ağu 2026'da kota kısıtı nedeniyle bu oturuma ERTELENDİ** — sıradaki
    oturumun ilk işi bu olmalı.
13. **RAG tabanlı "bu konuda soru sor" mini sohbet** — Perplexity/Artifact
    tarzı soru-cevap; ChromaDB semantic search (embedding_port) + Groq analiz
    hattı (analysis_port) zaten var, `AnalysisPort`'a yeni bir
    `answer_question` metodu olarak modellenebilir. Portfolyo değeri yüksek
    ama en büyük iş — kendi mimari tasarım turu ister. (19 Ağu 2026 rakip
    taraması, madde #7) **19 Ağu 2026'da kota kısıtı nedeniyle bu oturuma
    ERTELENDİ** — madde 12'den sonra ele alınmalı.
17. **Özet (summary) clickbait başlığı papağan gibi tekrarlamamalı** (19 Ağu
    2026, kullanıcı örnek verdi: "Fenerbahçe'ye müjde! Barcelona istiyor" gibi
    bir başlıkta özet de aynı belirsizliği koruyordu — hangi oyuncu (örn.
    Livakovic) olduğu içerikte varken özete yansımıyordu). Groq prompt'u
    (`adapters/analysis/common.py`) özetin başlıktaki clickbait/belirsizliği
    ÇÖZMESİNİ, içerikten somut isim/varlık çıkarmasını isteyecek şekilde
    güçlendirilmeli. Bounded bir prompt-engineering işi, kendi test turu ister
    (gerçek örnek haberlerle önce/sonra karşılaştırması).
16. **Admin panelinde /admin/users tablosu sıralanabilir olmalı** (19 Ağu 2026,
    kullanıcı istedi) — sahibinden.com tarzı: sütun başlığına (ekstra buton
    YOK, doğrudan yazının üstüne) tıklayınca sıralanır. 3 durumlu döngü:
    1. tık = artan, 2. tık = azalan, 3. tık = varsayılana (sırasız/orijinal)
    döner. Rol/Tier/Kayıt tarihi/Durum sütunlarının hepsi için geçerli —
    örnek: rol sütununa basınca önce moderatörler sonra adminler üstte
    gözükmeli (rank'e göre). Bounded bir frontend işi (`frontend/app/admin/
    users/page.tsx`), backend değişikliği gerekmiyor (mevcut liste zaten
    tamamı çekiyor, client-side sort yeterli).
15. **Test paketi sağlık denetimi** — 19 Ağu 2026'da kullanıcı sordu: "674
    test" büyüklük gösterir ama tek başına sağlık göstergesi değil, atıl/
    anlamsız/artık gerçek davranışı doğrulamayan testler birikmiş olabilir.
    Ayrı bir oturumluk iş: test dosyalarını tarayıp (1) hâlâ var olan kodu mu
    test ediyor, (2) mock'un kendisini mi test ediyor (gerçek davranışı
    değil), (3) aynı şeyi tekrar tekrar mı doğruluyor gibi sorularla atıl
    olanları temizle/birleştir.
14. ~~Kullanıcı banlama (moderatör/admin)~~ — ✅ 19 Ağu 2026'da tamamlandı.
    `PATCH /admin/users/{id}/active` — `update_user_role` ile birebir aynı
    kademeli yetki deseni (hedefin rolü actor'dan KESİNLİKLE düşük olmalı,
    owner hiç hedef olamaz, kendi kendini banlayamazsın), banlarken
    `delete_sessions_for_user` ile tüm oturumlar da düşürülür. Admin panelinde
    durum sütununda Banla/Banı Kaldır butonu.
19. ~~Arama ilişkisel sorgu genişletme (query expansion)~~ — ✅ 20 Ağu 2026'da
    tamamlandı, tek oturumda planlanıp uygulandı (spec: `docs/superpowers/
    specs/2026-08-20-arama-iliskisel-genisletme-design.md`). "İstanbul"
    araması "Beykoz" gibi ilişkili haberleri de düşük skorla yakalasın diye
    Groq'a `QueryExpansionPort` (`GroqQueryExpander`, cache'li
    `CachingQueryExpander`) üzerinden ikincil terim üretiliyor;
    `NewsService.hybrid_search` bunu `_keyword_relevance`'a `secondary_terms`
    olarak geçiyor, tamamen fail-open (Groq başarısız olursa eski davranış
    aynen sürer). `SEARCH_QUERY_EXPANSION_ENABLED` ile açık/kapalı.
    `get_news_service` DI'da `build_query_expander(get_cache())` ile bağlandı.

### Kasıtlı Kapsam Dışı (fayda/maliyet uygun değil)
K8s/Helm, Qdrant migration, CQRS, NTV Playwright scraper, Twitter/X entegrasyonu,
custom (Stripe dışı) billing portalı, App Store/Play Store (sadece PWA)

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
- **nginx routing (güncel, 18 Ağu 2026'da doğrulandı):** `/api/v1/` kendi location bloğunda prefix KORUNARAK proxy'lenir (`proxy_pass http://api/api/v1/`); diğer tüm rotalar (`/news/...`, `/health`, `/ws/feed`) `location /api/` ile `/api/` prefix'i SIYRILARAK proxy'lenir (`proxy_pass http://api/`) — yani dışarıdan `/api/news/search` → backend'de `/news/search`. `/api/` bloğunda WebSocket `Upgrade`/`Connection` header'ları VAR (8 Temmuz 2026'da eklendi). Bu iki eski gotcha (double-prefix, eksik WS header) uzun süre önce kapatılmıştı — burada sadece güncel/doğru routing şeması kayıtlı, geçmişteki hatalı halini merak edersen CHANGELOG'a bak.
- **nginx `add_header` mirası:** bir server/location kendi `add_header`'ını tanımlarsa üst context'ten (`http{}` dahil) HİÇBİR `add_header` miras alınmaz — tek tek ekleneni değil, TÜMÜNÜ iptal eder. Bir header'ın her yere gitmesini istiyorsan hepsini AYNI context'te topla (18 Ağu 2026'da CSP/X-Frame-Options vb.'nin sessizce hiç gitmediği bulundu, bkz. CHANGELOG "v2.1.1"). Ayrıca: `nginx.conf` host'ta bind-mount edilmiş bir dosyaysa, `git pull` sonrası `nginx -s reload` YETMEZ (git dosyayı unlink+rename ile değiştirdiği için container eski inode'a bakmaya devam eder) — `docker compose up -d --force-recreate nginx` gerekir.
- **WebSocket endpoint'ini `curl`/`wget` ile test etme** — ikisi de gerçek WS handshake yapmaz, gördüğün 404 hem "route yok" hem "araç anlamıyor" anlamına gelebilir, ayırt edemezsin. Gerçek istemci kullan: Python `websockets` kütüphanesi (`websockets.connect(...)`, red durumunda `InvalidStatus` + gerçek HTTP status/header verir) ya da Node'un yerleşik `WebSocket`'i.
- **Groq modelleri zamanla TAMAMEN kaldırılabiliyor** (404 `model_not_found`, rate limit DEĞİL) — fail-open bir analiz pipeline'ında bu sessizce nötr/varsayılan sonuca düşer, hiç alarm çalmaz (18 Ağu 2026'da `llama-3.1-8b-instant` böyle kayboldu, ~1 gün fark edilmedi). Şüphelenince `GET https://api.groq.com/openai/v1/models` ile güncel listeyi kontrol et. Güncel reasoning modelleri (`gpt-oss-*`) `reasoning`'i `message.reasoning` alanında `content`'ten AYRI döner (JSON parse'ı bozmaz); `qwen` ailesi `<think>` etiketini `content`'e GÖMER (bozar).
- **AWS SSM operasyon deseni:** `aws ssm send-command --document-name AWS-RunShellScript` içindeki komutlarda `git` kullanmadan önce `export HOME=/home/ubuntu` (SSM oturumunda `$HOME` set değil) + `git -c safe.directory=<repo-path>` (root/farklı kullanıcı sahipliği "dubious ownership" hatası verir) gerekir. Windows'taki native `aws.exe`'ye Git Bash'ten `file:///tmp/...` gibi bir paramfile yolu VERME — hiçbir `--parameters`/`--policy-document`/vb. argümanında path'i doğru çözemiyor; JSON'u her zaman inline (gerekirse `$(cat ...)` ile) geç.
- **Otomatik saldırgan engelleme kapsamı (19 Ağu 2026'da kullanıcı sorunca netleşti):** var olan tek savunma nginx `limit_req_zone` (IP başına genel hız sınırı, `infra/nginx/*.conf`) + slowapi endpoint bazlı limitler (login 15/dk, forgot-password 10/dk vb.) — ikisi de sadece o anki isteği YAVAŞLATIR/429 döner, KALICI bir IP ban/WAF/fail2ban YOK. Gerçek bir IP ban istenirse ayrı bir iş (IP blocklist tablosu + nginx `deny` ya da fail2ban entegrasyonu) gerekir, mevcut rate limiting bunu vermez. **Kullanıcı bazlı banlama ayrı ve VAR** (`PATCH /admin/users/{id}/active`, v2.2 — bkz. YOL HARİTASI madde 14) ama bu IP değil hesap seviyesinde, anonim/kayıtsız bir saldırganı durdurmaz.
- **`get_current_user` (zorunlu) X-API-Key'i ASLA çözmez (19 Ağu 2026 canlı testte bulundu):** admin router'ında yeni bir yazma endpoint'i eklerken `current_user: User = Depends(get_current_user)` kullanırsan, router-level `require_moderator`/`require_admin` X-API-Key'i kabul etse bile handler içindeki `get_current_user` → `get_optional_user` zinciri sadece session cookie/token/X-User-Key tanır, X-API-Key'i HİÇ görmez — sonuç: makine-makine erişimi (X-API-Key) router'dan geçer ama handler'da 401 alır. Doğru desen `update_user_tier`'da zaten vardı: `actor: Optional[User] = Depends(get_optional_user)`, `actor is None` ise (X-API-Key) rank-comparison/self-check atlanır. `update_user_active`'de bu hatayı yapıp canlı testte yakaladık, düzeltildi — yeni bir admin-yazma endpoint'i eklerken bu deseni kopyala, `get_current_user`'ı değil.
- **slowapi + çoklu worker gotcha'sı (19 Ağu 2026 güvenlik denetiminde bulundu):** prod `uvicorn --workers 2` ile çalışıyor; `limiter.py`'de `storage_uri` set edilmezse slowapi varsayılan olarak in-memory sayaç kullanır ve HER worker kendi ayrı sayacını tutar — kodda `"15/minute"` yazsa da istekler worker'lara round-robin dağıldığı için limit fiilen ~2 katına kadar gevşer (canlıda art arda 18 login denemesiyle doğrulandı, hiç 429 gelmedi). Çözüldü: `limiter = Limiter(..., storage_uri=REDIS_URL, in_memory_fallback_enabled=True)` — zaten cache için kurulu Redis'i paylaşıyor. **REDIS_URL prod'dan kaldırılırsa rate limit sessizce ~2x gevşer, hata vermez** — bunu unutma.
- **`nexstream-deploy` IAM kullanıcısı artık AdministratorAccess DEĞİL (19 Ağu 2026 güvenlik denetimi):** `NexStreamDeployMinimal` policy'sine scope'landı — sadece EC2 describe/start/stop/reboot + SSM SendCommand/GetCommandInvocation/DescribeInstanceInformation, hepsi `i-0608c897a3d8ca3f3` ile sınırlı (DEPLOY.md'de belgelenen gerçek kullanım). Bunun dışında bir AWS eylemi (S3, IAM, RDS, Budgets dahil — `aws budgets describe-budgets` bile artık 403 verir) gerekirse bu kimlikle YAPILAMAZ, kullanıcıya sor (geçici AdministratorAccess ya da Console). Kendi IAM policy'sini bile artık düzenleyemiyor (`iam:CreatePolicyVersion` yok) — kasıtlı.
- **v1.12 öncesi durum taraması (bu session'da yapıldı):** Responsive/erişilebilirlik/SEO/tema-performans-profili maddelerinin hiçbiri henüz başlamadı; sadece dashboard sayfasında kısmi bir skeleton-loading deseni var (diğer sayfalarla tutarsız). Yeni bir session bu maddelere başlarken sıfırdan tasarlamalı.
- **v1.11 sonrası yeni env var'lar:** `FRONTEND_URL` (boş — prod'da gerçek domain ile set edilmeli, şifre sıfırlama linki için), `PASSWORD_RESET_TTL_MINUTES` (60), `SEARCH_RECENCY_DECAY_FLOOR` (0.5), `SEARCH_RECENCY_WINDOW_DAYS` (30), `CHROMA_RETENTION_DAYS` (90 — 0 kapatır), `DB_RETENTION_DAYS` (0 — kapalı, açarsan Postgres'ten KALICI siler), `RETENTION_HOUR_UTC` (4), `EMAIL_VERIFICATION_TTL_MINUTES` (1440 — v1.15, e-posta doğrulama linki geçerlilik süresi), `EXPORT_MAX_ROWS` (20000 — v1.16, ham veri export üst satır sınırı), `WS_MAX_CONNECTIONS_PER_USER` (5 — v1.18, `/ws/feed` per-user tavan), `WS_MAX_TOTAL_CONNECTIONS` (500 — v1.18, `/ws/feed` global tavan), **v2.0 embedder ayarları:** `EMBEDDER_MODE` (`http` — `local` sadece Docker'sız geliştirme), `EMBEDDER_URL` (`http://embedder:8000`), `EMBEDDER_MODEL_NAME` (`paraphrase-multilingual-MiniLM-L12-v2`), `EMBEDDER_CONNECT_TIMEOUT` (2.0), `EMBEDDER_READ_TIMEOUT` (5.0), `EMBEDDER_BATCH_READ_TIMEOUT` (30.0), `EMBEDDER_RETRIES` (1), **v2.1 owner rolü + gerçek e-posta:** `OWNER_EMAILS` (boş — virgülle ayrılmış, DB'ye dokunmadan owner sayılır, tek kaynak bu env veya elle yazılan `role='owner'`), `EMAIL_PROVIDER` (`auto` — `smtp`/`resend`/`console` ile zorlanabilir), `SMTP_HOST` (`smtp.gmail.com`), `SMTP_PORT` (587), `SMTP_USER`/`SMTP_PASSWORD` (Gmail app password — normal login şifresi DEĞİL), `SMTP_FROM` (boşsa `EMAIL_FROM` kullanılır), `SMTP_STARTTLS` (`true`), `SEARCH_QUERY_EXPANSION_ENABLED` (`true` — v2.2, arama sorgu genişletme açık/kapalı anahtarı).
- **v2.0 nginx dersi:** nginx `upstream` bloklarını AÇILIŞTA çözer — tek bir upstream host'u ayakta değilse `[emerg] host not found in upstream` ile nginx HİÇ açılmaz ve API dahil bütün site çöker (28 Tem 2026'da grafana durdurulunca yaşandı). **Opsiyonel/ikincil upstream'ler değişkenli `proxy_pass` + `resolver 127.0.0.11` ile lazy çözümlenmeli** (grafana için yapıldı, prod ve dev conf'larda). `app`/`frontend` bilinçli olarak upstream bloğu olarak bırakıldı — onlar zaten zorunlu.
- **v2.0 Next.js standalone dersi:** Docker her container'a otomatik `HOSTNAME=<container-id>` koyar; Next.js standalone `server.js` buna bind eder ve o isim TEK bir ağ arayüzüne çözülür. Container iki ağdaysa (frontend + backend) nginx diğer ağdan ulaşamaz → **her temiz deploy'da 502**. `frontend/Dockerfile`'da `ENV HOSTNAME=0.0.0.0` şart. Log'daki "Network: http://0.0.0.0:3000" satırı bilgi amaçlıdır, bind adresini GÖSTERMEZ — ona bakıp teşhisi geri çekme.
- **v2.0 ChromaDB imaj dersi:** Bu imajda `curl`/`wget`/`python`/`nc` YOK, sadece `bash` var — healthcheck HTTP yoklamasını `/dev/tcp` ile elle kurmak zorunda (`exec 3<>/dev/tcp/localhost/8000 && printf "GET /api/v2/heartbeat HTTP/1.0\r\n\r\n" >&3 && head -1 <&3 | grep -q 200`). `/api/v1` yolu chroma 1.x'te kaldırıldı, `/api/v2` kullan.
- **Resend sandbox kısıtı (v1.15'te bulundu, TÜM ResendEmailAdapter gönderimlerini etkiler):** `resend.com/domains`'te doğrulanmış bir domain yoksa, `RESEND_API_KEY` gerçek/prod modda bile olsa sadece hesap sahibinin KENDİ e-postasına mail gönderilebilir — başka adrese denemek 403 ile patlar (sessizce loglanır, akışı bozmaz). Prod'a domain doğrulaması yapılmadan çıkılırsa hesap sahibi dışındaki gerçek kullanıcılar hiç mail almaz.
- **🔴 Canlıda HİÇBİR e-posta gönderilmiyor (29 Tem 2026'da bulundu):** prod `.env`'de `RESEND_API_KEY` BOŞ → `get_email_adapter()` sessizce `ConsoleEmailAdapter`'a düşüyor, mailler sadece loglanıyor. Doğrulama, şifre sıfırlama, digest, keyword alert — hepsi etkili. Lokal `.env`'de gerçek key var, prod'a hiç kopyalanmamış. Bu, "internal ağ" vakasıyla aynı sessiz işlevsizlik deseni.
- **SMTP yolu doğrulandı (29 Tem 2026):** `nexstream_engine` ve `nexstream_worker` container'larından `smtp.gmail.com:587` bağlantısı + STARTTLS handshake ÇALIŞIYOR — AWS 587'yi engellemiyor. Digest maili `scheduler`'da DEĞİL `app` içinde çalışıyor (`main.py:114`), o yüzden `scheduler`'ın sadece internal `backend` ağında olması mail için sorun değil.
- **Prod DB adı `nexstream`, `nexstream_db` DEĞİL** — SSM üzerinden `docker exec nexstream_db psql -U nexstream -d nexstream`.
- **Rol ve tier BAĞIMSIZ eksenler:** `ADMIN_EMAILS` bootstrap'i sadece `role`'ü etkiler, `tier`'a dokunmaz → "admin ama Ücretsiz kullanıcı" hali normaldir (owner rolü işi tam bunu çözüyor).
- **Ders — sessiz veri kaybı deseni:** `save_article()`'daki id-propagation bug'ı aylarca fark edilmeden ChromaDB indexlemeyi sessizce devre dışı bırakmıştı (exception fırlatmıyordu, sadece `article.id` None kalıyordu ve çağıran kod bunu es geçiyordu). Yeni bir "kaydet → sonra ID'ye ihtiyaç duyan bir şey yap" akışı eklerken, ORM nesnesinin PK'sının domain nesnesine gerçekten geri yazıldığını (`refresh()` + atama) doğrula — `user_repository.py::create_user` doğru pattern.
- **v2.1 ders — env-var tabanlı yetki bootstrap'ı (`ADMIN_EMAILS`/`OWNER_EMAILS`) sadece kayıt sırasında email normalize edilirse güvenlidir:** kontrol tarafı (`has_owner_role`/`has_admin_role`) email'i lowercase'liyor olması YETMEZ — `register()` de aynı normalizasyonu (strip+lowercase) uniqueness kontrolünden ÖNCE yapmazsa, bir case-varyantı (`Erenk897@gmail.com`) ile kayıt olmak farklı bir DB satırı yaratıp yine de lowercase edilmiş env-set eşleşmesinden geçer → yetki yükseltme. Yeni bir email-eşleşmeli bootstrap/yetki deseni eklerken kayıt/lookup'ın HER İKİ ucunun da aynı normalizasyonu uyguladığını doğrula.
- **v2.1 ders — bir dosyada `user.tier`'ı `effective_tier`'a çeviren bir görev bittiğinde, o DOSYADA kalan tüm `user.tier` okumalarını grep'le taramadan "bitti" deme:** owner rolü işinde 3 ayrı frontend dosyasında (`live-feed-context.tsx`, `NewsCard.tsx`, `dashboard/search/page.tsx`) plan bu dönüşümü hiç listelemediği için unutulmuştu — sadece final whole-branch review'da yakalandı (owner'ın WS canlı akışı hiç bağlanmıyordu). Aynı ders `_check_*` sağlık kontrolü gibi "N tane benzer nokta var" desenlerinin hepsi için geçerli.
- **Local ve prod AYNI paylaşılan `GROQ_API_KEY`'i kullanıyor (20 Ağu 2026'da bulundu):** local `.env` ve prod `.env` içindeki anahtar birebir aynı — local'de `docker compose up -d` ile worker/scheduler'ı bir süre açık bırakmak (test/geliştirme amaçlı), PROD'un worker'ıyla AYNI günlük Groq token bütçesini (200.000 TPD, "14.400 req/gün" YANILTICI — gerçek kısıt istek sayısı değil TOKEN, bkz. bir alt madde) paylaşıp tüketiyor. Normal prod trafiği tek başına çok düşük (48 saatte tek "yeni haber" partisi görüldü) ama local+prod aynı anda çalışırsa (özellikle local DB'de çok sayıda "yeni" sayılan haber varsa — ör. `docker compose down -v` sonrası temiz/boş DB) kota dakikalar içinde tükenebilir. Local'de uzun süreli worker/scheduler testi yapacaksan ayrı bir Groq key kullanmayı düşün ya da testi kısa tut, sonrasında **mutlaka `docker compose down`**.
- **Groq "TPD" (tokens per day) rate limit'i ismine rağmen KISA süreli/sliding gibi davranıyor:** 429 yanıtındaki `Retry-After` birkaç dakika (gözlemlenen: 3-7 dakika) — "gün sonuna kadar tükendi" DEĞİL, kısa bir tıkanıklık penceresi. `GroqAnalyzer` zaten bu header'ı okuyup bekliyor (worker çökmez, sadece o pencerede analiz gecikir) — panik gerekmez, `docker logs nexstream_worker | grep "rate limit"` ile durumu izle.
- **Türkçe ek kırpma (`_stem_tr`) + keyword arama substring bug'ı (20 Ağu 2026'da canlıda bulundu):** `_canonical_terms`/`_keyword_relevance` (news_service.py) eskiden kökü metnin HERHANGİ bir yerinde arıyordu (`t in text`, ham Python substring). "Adana" araması kökü "ada"ya iniyor, bu kök "havadan" kelimesinin ORTASINDA da eşleşiyordu → "Adana" araması alakasız "havadan" geçen bir habere en yüksek skorla gidiyordu. Düzeltme: eşleşme artık kelime BAŞINA sabitli (`\bterim` regex, `re.compile(r"\b" + re.escape(t))`) — çekimli formları (kökle başlayan kelimeler) hâlâ yakalıyor ama kelime ortasında rastgele bir alt dizi olarak eşleşmiyor. Yeni bir stem/substring tabanlı eşleştirme eklerken bu deseni kopyala, ham `in` kullanma.
- **Tek instance'lık background task + çoklu uvicorn worker = sessiz duplikasyon (20 Ağu 2026'da canlıda bulundu — slowapi notuyla AYNI KÖK NEDEN kategorisi):** `main.py`'nin `lifespan`'inde `asyncio.create_task(...)` ile başlatılan HER background job (newsletter_job, retention_job, broadcast poller) prod'da `--workers 2` olduğu için İKİ AYRI PROCESS'TE bağımsız kopyalanıyor. Newsletter job'da bu, abone günde 2 mail almasına yol açtı (ikisi de aynı 09:00 UTC hedefine uyanıp gönderiyordu) — Postgres `pg_try_advisory_lock`/`pg_advisory_unlock` ile düzeltildi (`newsletter_job.py::_send_digests`, kilidi alamayan worker o döngüyü sessizce atlar). Retention job aynı sorunu YAŞAMIYOR çünkü idempotent (delete-before-cutoff + upsert reindex, iki kez çalışsa da zararsız) — ama YENİ bir "günde bir kez, yan etkili" background job eklerken (ör. bildirim gönderimi) varsayılan olarak advisory-lock deseni gerektiğini varsay, idempotent olduğunu KANITLAMADIKÇA.
- **Bir metrik/rozet iki farklı yerde iki farklı ALGORİTMA ile hesaplanırsa tutarsızlık garanti (20 Ağu 2026'da canlıda bulundu):** kart footer'ındaki "N kaynak doğruluyor" rozeti (`corroboration_count`, entity-overlap tabanlı, ingest anında hesaplanıp DB'ye yazılıyor) ile "Kaynaklar" panelinin arkasındaki `get_story_cluster` (SADECE ChromaDB semantik embedding eşiği 0.72) hiç aynı şeyi ölçmüyordu — rozet "2 kaynak" derken panel "kaynak bulunamadı" gösterebiliyordu. Düzeltme: `_find_corroborating_articles` yardımcı metodu eklendi (`_count_corroboration` ile AYNI kriteri paylaşıyor), `get_story_cluster` artık bunu semantik sonuçlarla BİRLEŞTİRİYOR — rozetin saydığı her kaynak panelde garanti görünüyor. Aynı veriyi farklı yerlerde gösteren iki UI elemanı varsa (sayı + liste, özet + detay) altlarındaki hesaplamanın AYNI fonksiyonu paylaştığını doğrula, "yaklaşık aynı sonucu verir" varsayma.
- **Emoji glifin rengi CSS `color` ile kontrol edilemez — footer ikon butonları (20 Ağu 2026'da kullanıcı bulgusu):** `NewsCard`'daki aksiyon butonları (İlgili/Kaynaklar/Dinle/Kaydet) eskiden çıplak emoji + `var(--text3)`, arka plan/kontur yoktu; kaydet ikonu (🔖/🏷) özellikle küçük (0.85rem) ve hiçbir temada "buton" gibi görünmüyordu. Emoji'nin kendi (platform bağımlı, çoğunlukla renkli) glifi CSS `color`'dan etkilenmediği için görünürlüğü emoji rengine değil ÇEVRESİNDEKİ konteynıra dayandırmak gerekiyor — `globals.css::.icon-chip` (+ `.icon-chip--active`, `.icon-chip--iconOnly`) eklendi: hafif zemin (`rgba(0,0,0,.1)` — bilinçli DÜŞÜK tutuldu, yüksek opaklık koyu temalarda sorun değil ama gündüz temasında (açık zemin + koyu metin) kontrastı TERS yönde düşürüyordu, relative-luminance hesabıyla doğrulandı) + `var(--border2)` kontur + `var(--text2)` metin (text3 değil — text3 bazı temalarda küçük metin için WCAG AA sınırına (4.5:1) marjinal kalıyordu). Yeni bir ikon-only/az metinli aksiyon butonu eklerken `.icon-chip` class'ını kullan, çıplak emoji + inline renk KULLANMA.
