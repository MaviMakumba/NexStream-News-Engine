# NexStream News Engine — Değişiklik Tarihçesi

Bu dosya kronolojik geliştirme anlatısını taşır: hangi sürümde ne yapıldı, hangi bug
bulunup nasıl düzeltildi, hangi karar neden alındı. **Canlı/güncel referans için**
(mimari, kritik kararlar, güncel durum, kodlama kuralları, komutlar, kalıcı
gotcha'lar) `CLAUDE.md`'ye bak — bu dosya sadece "buraya nasıl geldik" sorusuna
cevap verir, her session başında okunması gerekmez.

18 Ağustos 2026'da, `CLAUDE.md` ~700 satıra ulaşıp "yaşayan dokümantasyon"dan
"arşiv"e dönüşmeye başlayınca bu dosyaya ayrıştırıldı — tüm tarihli
`✅ vX.Y — ... TAMAMLANDI` blokları buraya taşındı, `CLAUDE.md`'de sadece güncel
durumun özeti + gerçekten bekleyen işlerin kısa listesi kaldı.

---

## TAMAMLANAN ÖZELLİKLER (v1.2.0)

### Hybrid Search
- `POST /news/search`: ChromaDB (semantic) + PostgreSQL (keyword) birleşik
- Coverage-based skor, normalize embedding, `1/(1+distance)` formülü
- **v1.11 sonrası:** nihai skor `relevance * recency_decay` (çarpımsal) —
  `NewsService.hybrid_search`/`_decay_factor`'a bak

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
- Model: `llama-3.1-8b-instant` (70B → 8B, TPM 3× daha yüksek) — **18 Ağustos
  2026'da Groq bu modeli tamamen kaldırdı, bkz. "v2.1.1" bloğu aşağıda**
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
6. **Türkçe arama iyileştirmesi** — morfolojik suffix stripping (`_TR_SUFFIXES`), `_stem_tr()`, `_tokenize()` token genişletme (bu formülün coverage bölenini şişirme bug'ı 18 Ağustos 2026'ya kadar fark edilmedi, bkz. "v2.1.1" bloğu)
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

## v1.12 → v2.1.1 arası tüm tarihli işler (kronolojik)

Eski detay plan: `C:\Users\eren8\.claude\plans\ancient-watching-crescent.md`

**✅ v2.1 — Owner rolü + kademeli rol yönetimi + gerçek e-posta gönderimi (17 Ağustos 2026, TAMAMLANDI, 18 Ağustos 2026'da prod'a deploy edildi):**
Spec: `docs/superpowers/specs/2026-07-29-owner-rolu-ve-gercek-email-gonderimi-design.md`. SDD (subagent-driven-development)
ile 25 task + 1 addendum (Task 21b) + final whole-branch review fix dalgası olarak uygulandı,
`feat/owner-role-email` dalı (`optimize/t3-small-ram`'dan ayrılmıştı) lokal fast-forward merge ile
kapatıldı, worktree/dal temizlendi. Dört parça: (1) `owner` rolü
(`user<moderator<admin<owner`, `OWNER_EMAILS` env bootstrap, API'den asla atanamaz — `_ASSIGNABLE_ROLES`
allowlist, migration gerekmedi); (2) owner her yerde Enterprise muamelesi — domain'de saf
`effective_tier(tier, is_owner)` + `auth_utils.user_effective_tier(user)` sarmalayıcı (domain hâlâ
`settings` import etmiyor), 8 backend gating noktası + 6 frontend yüzeyi dönüştürüldü, public
`/news/search` doğrulanmış şekilde DEĞİŞMEDİ; (3) kademeli rol yönetimi (hedefin rolü < aktörün rolü
VE atanacak rol <= aktörün rolü) — Task 12'de plan/spec çelişkisi bulundu (brief `require_admin`'i
route'ta tutuyordu, spec sadece router-level `require_moderator` + iç rank mantığı istiyordu),
kullanıcı kararıyla spec galip geldi; (4) `SmtpEmailAdapter` (Gmail SMTP) + ortak `_HtmlEmailAdapter`
ara sınıfı + `EMAIL_PROVIDER=auto|smtp|resend|console` + `/health`'in `email` alanı.
**Final whole-branch review'da (Opus) bulunup DÜZELTİLEN 1 Kritik + 4 Önemli bulgu:**
(a) 🔴 **en kritik** — `OWNER_EMAILS`/`ADMIN_EMAILS`
kontrolü email'i lowercase'liyordu ama `register()` kayıt sırasında normalize etmiyordu, yani
`Erenk897@gmail.com` (case-varyantı) diye kayıt olan biri owner yetkisi kazanabiliyordu (owner
e-postası bu public repo'nun commit geçmişinde zaten açık) — `register()` artık uniqueness kontrolünden
ÖNCE email'i strip+lowercase yapıyor; (b) 3 frontend gate hâlâ ham `user.tier` okuyordu
(`live-feed-context.tsx`, `NewsCard.tsx`, `dashboard/search/page.tsx`) — owner'ın WS canlı akışı hiç
bağlanmıyordu; (c) `EMAIL_PROVIDER=smtp` ama kimlik bilgisi boşsa hiçbir yerde uyarı yoktu, `/health`
yalancı "smtp" diyordu — artık `"smtp (kimlik eksik)"`; (d) Gmail SMTP `From` başlığı `smtp_user`dan
farklı bir varsayılana düşüyordu (Gmail relay reddedebilir/değiştirebilir) — fallback artık
`smtp_from or smtp_user or email_from`; (e) kademeli rol yönetiminin asıl kuralı (atanan rol aktörün
kendi rütbesini aşamaz) hiç test edilmemişti.

**✅ v2.1.1 — v2.1'in prod'a deploy'u SIRASINDA bulunan 3 gerçek canlı bug + sonraki oturumda bulunan
3 daha (18 Ağustos 2026, TAMAMLANDI):** prod hâlâ 29 Temmuz'daki v2.0 commit'indeydi (owner rolü hiç
canlıda değildi, kullanıcı "pro değilsin" görüyordu) — `git push` + sunucuda `pull` + `docker compose
up -d --build app worker frontend` ile deploy edildi. Ardından kullanıcının "arama/semantic/tag/duygu
analizi uçtan uca çalışıyor mu" isteği üzerine yapılan canlı doğrulama sırasında 3 bağımsız, gerçek
prod bug'ı bulundu (hiçbiri planlı değildi, hiçbiri bu oturumun deploy'undan KAYNAKLANMADI — ikisi
zaten günlerdir sessizce bozuktu):
1. 🔴 **En kritik — Groq `llama-3.1-8b-instant` modeli TAMAMEN KALDIRILMIŞ** (17 Ağu 2026 ~08:35 UTC'den
   beri, `HTTP 404 model_not_found`). `analyze_text()` hata yutup nötr fallback döndüğü için (bilinçli
   "servis çökmesin" tasarımı) HİÇBİR alarm çalmadı — ~1 gündür canlıdaki HER haber sessizce
   sentiment=Neutral/topic=Other/entities=boş alıyordu, bu da gündem (trending) ve "ilgili haberler"i de
   BOŞ gösteriyordu (entity overlap'e dayandıkları için — 3 farklı belirti, TEK kök neden). Cursor
   bazlı ikili arama ile regresyonun tam ne zaman başladığını (`/api/v1/news?cursor=N` ile tarihe göre)
   tespit ettik. **Çözüm:** model `openai/gpt-oss-20b`'ye geçti. Kod deploy sonrası birkaç dakika
   içinde gündem/ilgili-haberler kendiliğinden düzeldi (yeni haberler doğru analiz edildi), eski ~1
   günlük nötr haberler geriye dönük düzeltilmedi (`reanalyze_all()` `entities is not None` olan
   satırları atlıyor — nötr fallback NULL değil boş dict yazdığı için bu endpoint onları YAKALAMIYOR,
   bilerek backfill yapılmadı, kullanıcı "gerek yok" dedi).
2. **`/ws/feed` prod'da HİÇ ÇALIŞMIYORDU** (muhtemelen hiç, o özellik yazıldığından beri) —
   `requirements.txt`'te `uvicorn==0.41.0` (bare, `[standard]` DEĞİL) ve `websockets`/`wsproto` hiç
   pinlenmemiş; uvicorn bu paketler olmadan WS protokolünü hiç tanımıyor, her upgrade isteği düz HTTP'ye
   düşüp Starlette router'ında 404 alıyordu. **Bu tamamen fark edilmeden kalmıştı çünkü:** (a) local
   venv'de `websockets` `google-genai` (Gemini döneminden kalma, `requirements.txt`'te YOK, hiçbir yerde
   import edilmiyor) üzerinden transitive kurulu geliyordu; (b) `tests/adapters/test_websocket.py`
   Starlette `TestClient`'ın in-process ASGI transport'unu kullanıyor, bu da gerçek `websockets` paketine
   HİÇ ihtiyaç duymuyor — testler bu sınıfta hiçbir zaman yakalayamaz. **Çözüm:** `requirements.txt`'e
   `websockets==16.0` eklendi (`uvicorn[standard]` DEĞİL — o extras httptools/uvloop/watchfiles de
   getirirdi, RAM optimizasyonu disiplinini bozardı).
3. Frontend `useLiveFeed.ts`: prod'da `NEXT_PUBLIC_API_URL=/api` (göreli) olduğu için
   `BASE.replace(/^http/,"ws")` no-op kalıyor, `new WebSocket("/api/ws/feed")` tarayıcıda senkron
   `SyntaxError` fırlatıyordu (göreli URL sayfanın şemasını [https] miras alır, WebSocket constructor'ı
   şemanın ws/wss olmasını zorunlu kılar) — try/catch'siz olduğu için ticker sessizce "bağlantı kesildi"
   durumunda donuyordu. `window.location`'dan açık `ws(s)://host+path` inşa edecek + constructor'ı
   try/catch'e alacak şekilde düzeltildi.

**Aynı oturumda kullanıcı isteğiyle yapılan ikinci tur (deploy sonrası):** kullanıcı security review +
arama kalitesi + CLAUDE.md büyüklüğü + main merge sordu, hepsi aynı oturumda halledildi:
4. 🔴 **nginx security header'ları hiç kullanıcıya ulaşmıyordu** — `X-Frame-Options`/`X-Content-Type-
   Options`/`Referrer-Policy`/`Permissions-Policy`/CSP `http{}` seviyesinde tanımlıydı (v1.17 denetiminde
   eklenmişti) ama 443 `server{}` bloğu kendi `add_header Strict-Transport-Security`'sini tanımladığı
   için nginx'in "bir context kendi add_header'ını tanımlarsa üst seviyedekiler TAMAMEN iptal olur"
   kuralı yüzünden hepsi sessizce gönderilmiyordu — canlıda `curl -sI` ile doğrulandı, v1.17'den beri
   hiç gitmemiş olabilir. Hepsi 443 server bloğuna taşındı (tek context). **Deploy'da ekstra ders:**
   nginx.conf host'ta bind-mount edilmiş bir dosya; `nginx -s reload` config'i doğru okur ama container
   `git pull`'un dosyayı unlink+rename ile DEĞİŞTİRDİĞİ eski inode'a bakmaya devam eder — sadece
   `docker compose up -d --force-recreate nginx` container'ı gerçekten yeni dosyaya bağlar. **Genel
   kural: bir bind-mount edilmiş config dosyasını `git pull` ile güncelledikten sonra `reload` yetmez,
   container'ı force-recreate et.**
5. **Türkçe ekli tek kelimelik arama sorguları alakasız sonuçlarla doluyordu** ("beşiktaşın" →
   Beşiktaş haberleri yerine icra dairesi/belediye ilanları). Kök neden: `hybrid_search`'ün coverage
   skoru `len(query_terms)`'e bölünüyordu, `_tokenize()` her kelimeyi HEM ham HEM kök haliyle 2 ayrı
   terim olarak listeye eklediği için ("beşiktaşın" → `["beşiktaşın","beşiktaş"]`), metinde sadece kök
   eşleştiği için kapsama %50'de kalıp skor yapay olarak yarıya düşüyordu (0.9 yerine 0.45) — bu da
   ChromaDB'nin ürettiği alakasız-ama-göreceli-yüksek (~0.5) semantik skorların altına düşmesine yol
   açıyordu. Yeni `_canonical_terms()`: her kelime için TEK terim (kökü, varsa) — kök her zaman
   orijinal kelimenin bir ön eki olduğundan (suffix-stripping), ikisini birden saymak hiçbir ek bilgi
   katmadan böleni şişiriyordu. `hybrid_search` artık SQL adayı için `_tokenize()`, skorlama için
   `_canonical_terms()` kullanıyor.
6. **`main` PR #33 ile senkronize edildi** — main 29 Temmuz'dan beri güncellenmemişti (57 commit geride,
   sıfır divergence — tertemiz fast-forward), `optimize/t3-small-ram`'daki tüm iş (v2.0→v2.1.1) bir PR
   ile `main`'e merge edildi.
7. **Güvenlik/altyapı taraması** (canlıda gerçekten kontrol edildi, kod değişikliği gerektirmeyenler):
   Cloudflare/CDN önden geçmiyor — DNS `nexstreamnewsengine.duckdns.org` doğrudan EC2 IP'sine (`63.178.
   59.10`) çözülüyor, CLAUDE.md'de "plan" olarak yazıyordu ama hiç kurulmamış (tek instance, WAF/CDN
   yok). `/api/docs` açık (bilinçli). Admin endpoint auth'suz denendi → doğru 401. Rate limiting
   (nginx+slowapi) çalışıyor. AWS maliyet analizi: `aws ce get-cost-and-usage` ile $100 kredinin
   ~$18,4'ü harcanmış, günlük yakım ~$0,93 (~$28/ay) — kredi mevcut hızla Kasım ortasında (Ocak 2027
   son kullanma tarihinden ~2,5 ay önce) tükenecek, bu bilgi sürdürülebilirlik tartışmasının girdisi
   oldu. Deploy/rebuild işlemlerinin AWS faturasına etkisi pratikte sıfır (instance zaten 7/24
   ücretlendiriliyor, build CPU'su ekstra fatura çıkarmıyor).
- **CLAUDE.md bölündü** — bu dosya (`docs/CHANGELOG.md`) o gün oluşturuldu, tüm tarihli anlatı buraya
  taşındı.
- **Kalıcı dersler (bu oturumdan):** (1) `curl`/`wget` ile WebSocket endpoint'i test ETME — gerçek
  handshake yapmazlar, gördüğün 404 hem "route yok" hem "araç anlamıyor" anlamına gelebilir, ayırt
  edemezsin; gerçek istemci kullan (Python `websockets`, Node'un yerleşik `WebSocket`'i). (2) Groq
  modelleri zamanla TAMAMEN kaldırılabiliyor (404 `model_not_found`) — periyodik `GET
  https://api.groq.com/openai/v1/models` kontrolü faydalı; güncel reasoning modelleri (`gpt-oss-*`)
  `reasoning`'i `content`'ten ayrı döner, `qwen` `<think>` etiketini content'e gömer (JSON parse'ını
  bozar). (3) AWS SSM operasyon deseni: `export HOME=/home/ubuntu` + `git -c safe.directory=<path>`
  gerekli (dubious ownership); Windows'taki native `aws.exe`'ye Git Bash'ten `--parameters
  file:///tmp/...` gibi bir paramfile yolu VERME, path'i doğru çözemiyor — inline JSON (gerekirse
  base64) geç. (4) nginx bind-mount edilmiş config dosyası `git pull` sonrası eski inode'a takılı
  kalabilir — `reload` değil `--force-recreate` gerekir.

**✅ v2.1.2 — API docs portalı + Grafana alerting + gerçek canlı yürüyüşte bulunan bug'lar + digest
formu (18 Ağustos 2026, aynı oturumun devamı, TAMAMLANDI):**
- **API docs portalı:** FastAPI metadata zenginleştirildi (versiyon/açıklama/contact/license/10 tag
  açıklaması), eksik `LICENSE` dosyası (MIT) eklendi, `docs/NexStream.postman_collection.json`
  eklendi. **Bunu açarken 2 gerçek bug bulundu, ikisi de aynı kök problemin farklı katmanları:**
  (1) o günün erken CSP eklemesi Swagger UI'ın CDN'den (`cdn.jsdelivr.net`) çektiği JS/CSS'i
  engelleyip beyaz sayfa veriyordu — CSP'ye CDN eklendi; (2) CSP düzelince Swagger UI çalıştı ama
  `openapi_url`'i kök-mutlak (`/openapi.json`) ürettiği için nginx'in `/api/` prefix'ini bilmiyordu,
  tarayıcı `https://domain/openapi.json`'a gidip 404 alıyordu — uvicorn'a `--root-path /api` eklendi
  (Swagger UI'ın ürettiği URL'leri düzeltir, gerçek iç routing'i DEĞİŞTİRMEZ).
- **Launch/paylaşım içeriği:** `NEXT_PUBLIC_SITE_URL` hiç wire edilmemişti (Dockerfile'da ARG yok) —
  `robots.txt`/`sitemap.xml`/OG meta HAFTALARDIR kimsenin sahibi olmadığı `nexstream.news`'a işaret
  ediyordu, düzeltildi. `next/og`'un `ImageResponse`'ı Windows'ta `@vercel/og`'un gömülü font
  yükleyicisinde "Invalid URL" ile çöktüğü için (yerel `next start` ile doğrulandı), statik bir
  Pillow-üretimi OG görseline geçildi (PWA ikonlarıyla aynı yöntem, sıfır çalışma-zamanı riski).
  LinkedIn için hazır paylaşım metni kullanıcıya verildi.
- **README'ye "Nasıl Çalışır" bölümü** — kullanıcının "sayısal veriler + algoritma açıklamaları
  gerekli mi" sorusu üzerine: kalite/güvenilirlik skoru formülleri, hibrit arama sıralama formülü
  (bugünkü Türkçe-ek bug'ı gerçek örnek olarak), ve canlı Prometheus'tan çekilmiş (uydurma değil)
  gerçek sayılar (Groq gecikmesi, image boyutları, test süresi).
- **Grafana alerting** — iki provisioned alert kuralı: "1 saattir yeni haber işlenmedi" (mevcut
  `nexstream_articles_processed_total`) ve "analiz sürekli nötr fallback'e düşüyor" (yeni
  `nexstream_analysis_fallback_total` sayacı, `FallbackAnalyzer`'a eklendi — bugünkü Groq olayını
  ~15-20 dakikada yakalardı). **Kurulum sırasında Grafana'yı GERÇEKTEN ÇÖKERTEN bir hata yapıldı:**
  datasource'a elle sabit bir `uid: prometheus` vermeye çalışmak, Grafana'nın haftalardır kayıtlı
  auto-generated UID'li mevcut kaydıyla çakışıp "Datasource provisioning error: data source not
  found" ile Grafana'yı crash-loop'a soktu — birkaç dakika içinde canlı doğrulamada yakalanıp geri
  alındı, gerçek UID Grafana'nın kendi `/api/datasources` API'sinden okunup doğru şekilde tekrar
  kuruldu. **Genel ders: zaten haftalardır provisioning ile yönetilen bir Grafana kaynağının uid'ini
  SONRADAN elle sabitlemeye çalışma; gerçek/mevcut uid'i API'den oku.** Ayrıca worker'ın kendi
  Prometheus sayaçlarının HİÇ scrape edilmediği bulundu (worker ASGI değil, `/metrics` sunan bir HTTP
  sunucusu hiç yoktu — muhtemelen v1.6'dan beri) — `prometheus_client.start_http_server(9100)`
  eklenip yeni bir scrape job'u tanımlandı, canlıda gerçek verinin akmaya başladığı doğrulandı.
- **Kullanıcının canlı yürüyüşte bulduğu 6 gerçek bug:** (1) Landing hero'daki "Panele Git" ve "Demo
  Görüntüle" giriş yapmış kullanıcıda İKİSİ DE `/dashboard`'a gidiyordu — "Demo Görüntüle" artık
  sayfadaki canlı arama demosuna kaydırıyor. (2) "825+ Haber İndekslendi" istatistiği (VE ayrıca hero
  rozetindeki ikinci bir kopyası) v1.11-öncesi bir hata raporundan kalma donuk bir sabitti — artık
  `/health` + `/news/sources`'tan canlı çekiliyor. (3-4) Yukarıdaki API docs iki bug'ı. (5) Çıkış
  yap → tarayıcı GERİ tuşu → hâlâ giriş yapılmış görünüyordu — kök neden bfcache (tarayıcı önceki
  sayfayı donmuş JS durumuyla, mount effect'leri TEKRAR ÇALIŞTIRMADAN geri getiriyor); gerçek bir
  yetki açığı değildi (çerez sunucuda gerçekten geçersiz) ama yanıltıcıydı — `pageshow`/`persisted`
  dinleyicisiyle düzeltildi. (6) Pricing'de Kurumsal paket "Özel kaynak ekleme" vaat ediyordu ama
  kodda hiç yok — kullanıcı kararıyla "bize ulaşın" diye yumuşatıldı, tam private/per-user versiyonu
  (kullanıcı bazlı veri izolasyonu gerektirir, şu an sistemde YOK) ileriye bırakıldı.
- **Digest/bülten formu** — kullanıcı kendi hesabında hiç abonelik kaydı olmadığını fark edip
  "bu özellik hâlâ çalışıyor mu" diye sordu; DB kontrolünde `subscribers` tablosunda 0 satır çıktı.
  Kazı sonucu: backend `/subscriptions` sistemi v1.7'den beri TAM çalışır durumdaydı ama Next.js
  frontend'inde bunu açan HİÇBİR sayfa/form yoktu (muhtemelen Streamlit → Next.js geçişinde, v1.10,
  unutulmuş) — üstelik pricing sayfası "Günlük digest e-postası"nı Free pakette bile vaat ediyordu.
  `/subscriptions/{email}` GET/PATCH paylaşımlı admin `X-API-Key` istediği için (normal kullanıcı
  oturumuyla kendi durumunu okuyamaz), `/account`'un "kendi verin, session auth" desenini izleyen
  yeni bir `GET /account/newsletter` eklendi (sadece ön-doldurma için okuma); kaydetme mevcut public
  `POST /subscriptions/`'ı (zaten upsert) olduğu gibi kullanıyor. Hesap sayfasına sıklık/konu/kaynak/
  keyword tercihli bir kart eklendi.
- **AWS maliyet/Cloudflare araştırması:** `aws ce get-cost-and-usage` ile $100 kredinin ~$18,4'ü
  harcanmış bulundu, günlük yakım ~$0,93 (~$28/ay) — kredi Kasım ortasında (son kullanma tarihinden
  ~2,5 ay önce) tükenecek. Cloudflare'in DuckDNS subdomain'i için KULLANILAMAYACAĞI netleşti
  (Cloudflare bir zone'un TAMAMINA nameserver olmak ister, DuckDNS'in kendi zone'unun bir alt alan
  adını devredemezsin) — gerçek bir domain satın alınması gerekiyor, kullanıcıya açıklandı, karar
  bekliyor.
- **Kalıcı ders:** Aynı "sessizce çalışmıyor ama görünürde her şey normal" deseni bu oturumda 3.
  kez çıktı (worker metrikleri, digest UI'ı, gündem/ilişki grafı boşluğu) — **bir özelliğin backend
  tarafının var olması, kullanıcının ona GERÇEKTEN erişebildiği anlamına gelmez; her "tamamlandı"
  işaretli özelliği periyodik olarak uçtan uca (gerçek bir tarayıcıdan, gerçek bir hesapla) yürü.**

**✅ v2.0 RAM/disk optimizasyonu + CANLIYA ÇIKIŞ — `embedder` servisi + 7 gerçek repo bug'ı (29 Temmuz 2026, TAMAMLANDI ve DEPLOY EDİLDİ):**
- **🚀 SİTE CANLI: https://nexstreamnewsengine.duckdns.org** — AWS t3.small, gerçek Let's Encrypt sertifikası (27 Ekim 2026'ya kadar, certbot 12 saatte bir otomatik yeniliyor), 16 servis ayakta, boru hattı uçtan uca çalışıyor. **Sunucuya SSH ile DEĞİL, AWS SSM ile bağlanılıyor** (port 22 hem sandbox'tan hem kullanıcının ISP'sinden kapalı) — detay `DEPLOY.md` §2-AWS.
- **Bağlam:** 28 Temmuz'da AWS `t3.small`'a (2 vCPU / 1.9GB) yapılan deploy teknik olarak çalıştı ama RAM yetmedi, yığın sürekli swap'taydı. Kullanıcının net talimatı: **"HİÇBİR ŞEY PORTFOLYOMUZU BOZAMAZ"** — hiçbir servis yığından çıkarılmayacak, çözüm kodu makineye sığdırmak. Spec: `docs/superpowers/specs/2026-07-28-t3-small-ram-optimizasyonu-design.md`, plan: `docs/superpowers/plans/2026-07-28-t3-small-ram-optimizasyonu.md`.
- **Asıl mimari değişiklik — `embedder` servisi:** `app` ve `worker` SentenceTransformer'ı ayrı ayrı yüklüyordu. Model yeni bir `embedder` container'ına taşındı; ikisi de `HttpEmbedderAdapter(EmbeddingPort)` ile HTTP'den soruyor. `build_embedder()` kompozisyon noktası (`embedder_factory.py`), `analysis/factory.py` desenini izliyor. **`src/domain/` hiç değişmedi.** `embedder_mode="local"` Docker'sız geliştirme için duruyor ve o daldaki import BİLİNÇLİ olarak fonksiyon içinde — app/worker image'larında `sentence-transformers` kurulu DEĞİL, modül seviyesine taşınırsa o container'lar açılışta çöker (kaynağı denetleyen testler bunu kilitliyor).
- **Ölçülen sonuçlar:** app **132 MiB**, worker **96 MiB** (ikisi de eskiden modeli taşıyordu), embedder 633 MiB. Dev yığını toplam ~1,30 GiB. `nexstream_engine` artık **6 saniyede** healthy (eskiden 1-2 dakika). Image'lar: app/worker 1.55GB→**516MB**, scheduler 1.27GB→**233MB**.
- **BULUNAN 7 GERÇEK BUG (hiçbiri planda yoktu):**
  1. **Retention job'ı HİÇ silmiyormuş.** `delete_before()` `where={"published_at": {"$lt": cutoff_iso}}` kullanıyordu; ChromaDB `$lt`'yi YALNIZCA int/float için kabul edip ISO string'e `ValueError` fırlatıyor, hata da fonksiyonun kendi `except`'inde yutuluyordu → günlük ChromaDB temizliği her gece sessizce 0 vektör sildi, vektör deposu sınırsız büyüdü. **Mevcut test bunu göremiyordu çünkü MagicMock koleksiyon geçersiz `where`'i sorunsuz kabul ediyor.** Düzeltme: metadata sayfalanarak taranıyor (`RETENTION_SCAN_BATCH=1000`), eskiler Python'da seçilip `delete(ids=...)` ile siliniyor; `published_at` boş olanlar ATLANIYOR (boş string her cutoff'tan küçüktür, tarihi bilinmeyen her vektör silinirdi).
  2. **Redpanda heap == container limit.** `docker-compose.prod.yml`'de `--memory=768M` ve `memory: 768M` birebir aynıydı — 28 Temmuz'da Redpanda'yı hiç açılmaz yapan durumun ta kendisi. O gün SUNUCUDA elle düzeltilmiş ama REPO'YA GİRMEMİŞ; taze bir deploy aynı çökmeyi tekrar üretirdi. Heap 256M'ye çekildi.
  3. **Loki'de hiç retention yoktu**, loglar sonsuza kadar birikiyordu. `retention_period` tek başına yetmez — silmeyi compactor yapar ve `retention_enabled: true` olmadan Loki süreyi yok sayar.
  4. **`.dockerignore` `frontend/`'i dışlamıyordu** — `node_modules` + `.next` ile ~356MB backend image'larına giriyordu.
  5. **`COPY . .` sonrası `chown -R /app` tüm ağacı İKİNCİ KEZ katmanlıyordu** (407MB'lık ikiz katman). Kullanıcı artık kopyalamadan ÖNCE açılıyor, kopyalama `COPY --chown` ile yapılıyor.
  6. **Embedder named volume izin hatası:** Docker boş bir named volume'u image'daki AYNI yoldaki dizinin içeriği ve SAHİPLİĞİYLE başlatır; dizin image'da yoksa volume root'a ait doğar ve non-root kullanıcı yazamaz. `Dockerfile.embedder` artık `~/.cache/huggingface`'i açıkça oluşturup `appuser`'a veriyor.
  7. **`worker`'ın interneti YOKTU — prod'da hiç haber toplanmamış.** `backend` ağı `internal: true` ve `worker` yalnızca oradaydı, yani 17 RSS kaynağına da Groq API'sine de hiç ulaşamıyordu (`Temporary failure in name resolution`). **Sinsi tarafı: yığın tamamen sağlıklı görünüyordu** — tüm container'lar healthy, `/health` yeşil, arayüz açılıyor, ama veritabanı sonsuza kadar boş. Scraper exception'ı yutup `[]` döndüğü için (bilinçli tasarım) hiçbir yerde alarm çalmadı. Çözüm: açık bir `egress` ağı (bridge, internal DEĞİL); `worker` ve `backup` ona da bağlandı (`backup`'ın rclone offsite yüklemesi de aynı sebeple sessizce başarısız oluyordu). `app` eklenmedi — zaten `frontend` ağından çıkışı var.
  - **Aynı kök nedenin embedder'daki hâli:** model runtime'da indirilemiyordu. Çözüm ağ açmak DEĞİL, modeli `Dockerfile.embedder`'da **build anında image'a gömmek** oldu (embedder'ın dışarıya çıkmasına gerçekten gerek yok). Yan kazançlar: ilk açılış beklemesi kalktı (`start_period` 900s→180s), `hf-xet` tıkanma riski bitti, cache volume'ü gereksizleşti, `HF_HUB_OFFLINE=1` ile eksik dosya sessizce ağa uzanmak yerine net hata veriyor.
- **Test paketi 400sn → 22sn (18×).** En büyük pay (~108sn/124sn): `conftest.py`'deki `app_client` fixture'ı `engine`'i patch'liyordu ama `SessionLocal`'ı ETMİYORDU; `usage_tracking_middleware` her `/api/v1/` isteğinden sonra `_log_api_usage` açıyor, o da `SessionLocal()` ile GERÇEK psycopg2 bağlantısı deniyordu — psycopg2 senkron olduğu için event loop'u bağlantı timeout'u boyunca (~2sn) BLOKE ediyordu. Hata `except`'te yutulduğu için testler geçiyordu, sadece her biri 2 saniye yavaşlıyordu. Ayrıca: iki testte hata yolundaki `time.sleep(5)` (10'ar sn), bir testte Groq throttle'ı (4sn), `embedder_service`'in modül seviyesindeki torch import'u (10sn).
- **Faz C kısmaları (kullanıcıya görünen hiçbir özellik kaldırılmadı):** Redpanda heap 256M; embedder'da `OMP_NUM_THREADS=1`/`MKL_NUM_THREADS=1` (719,6→633 MiB, ölçüldü); Prometheus retention 30g→7g + 512MB tavan, Loki 7 gün. **ONNX int8 UYGULANMADI** — arama kalitesinden ~%1-2 ödün ister, kullanıcı onayı gerektirir.
- **Kalıcı dersler:** (1) Bir dış servisin sorgu/filtre API'sini MagicMock'la test etmek, o servisin gerçekte reddedeceği çağrıları görünmez kılar — filtre/sorgu sözdizimini en az bir kez GERÇEK servise karşı doğrula. (2) Docker image'ını `:latest` ile kullanma; pin ederken etiket numarasına değil çalıştırılabilirin kendi sürüm çıktısına bak. (3) `COPY . .` + `chown -R` sırası image boyutunu ikiye katlar — `COPY --chown` kullan. (4) Named volume'a bağlanacak dizini image'da önceden oluştur ve sahibini ayarla. (5) Testler geçiyor olması hızlı oldukları anlamına gelmez — `--durations` ve gerektiğinde cProfile ile bak; yutulan hatalar sessizce saniyeler yiyebilir. (6) **`internal: true` bir ağdaki container DNS bile çözemez ve bunun belirtisi çökme değil SESSİZ işlevsizliktir** — bir servisi o ağa koyarken "bu servis dışarıya çıkıyor mu?" diye açıkça sor. (7) **Deploy'u `/health` yeşil mi diye doğrulama, İŞ ÇIKTISIYLA doğrula** (kaç haber toplandı, kaç kayıt yazıldı) — healthcheck'ler sürecin ayakta olduğuna bakar, işini yaptığına değil.

### v1.12 — UX, Erişilebilirlik & SEO Cilası (frontend ağırlıklı) — ✅ TAMAMLANDI (20 Temmuz 2026)
1. ✅ **Responsive geçiş** — Navbar mobil menüsü (8 Temmuz) + dashboard/search/account/admin sayfalarının responsive taraması (20 Temmuz, detay aşağıda).
2. ✅ **Erişilebilirlik** — kontrast (9 tema), focus/aria/klavye (20 Temmuz, detay aşağıda). Bkz. mevcut global `:focus-visible` kuralı (`globals.css`) zaten iyiydi, sadece kontrast + aria/klavye eksikti.
3. ✅ **SEO** — go-live hazırlık turunda yapıldı (8 Temmuz, bkz. aşağıdaki blok): generateMetadata, robots.ts, sitemap.ts.
4. ✅ **Tema ince ayarı** — efekt yoğunluğu/performans profilleri (low/high) eklendi (20 Temmuz, detay aşağıda). Yeni tema eklenmedi (kapsam dışı bırakıldı, istenirse ayrı iş).
5. ✅ **Durum cilası** — auth loading state tutarlılığı (20 Temmuz). Search/admin sayfalarında zaten makul error/empty state'ler vardı, dashboard'daki skeleton deseni korundu.

### v2.0 — Public Launch (v1.12 sonrası)
1. ✅ **Domain & VPS — TAMAMLANDI (29 Temmuz 2026), site CANLI:** https://nexstreamnewsengine.duckdns.org — AWS Free Plan ($100 kredi, 28 Ocak 2027'ye kadar) köprü olarak kullanıldı; Oracle A1.Flex kapasitesi günlerce "Out of host capacity" verdiği için beklenmedi. t3.small (2 vCPU/1.9GB) + DuckDNS + gerçek Let's Encrypt. Kredi ~$25/ay yakıyor (compute+EBS+EIP) → ~4 ay ömür; durdurulunca ~$10/ay. Sunucu yönetimi SSH DEĞİL **AWS SSM** üzerinden (port 22 kapalı). Tarihsel plan değişikliği kaydı: ~~Hetzner CX22~~ — ❌ **22 Temmuz 2026'da PLAN DEĞİŞTİ:** kullanıcının bütçesi GERÇEKTEN $0/ay (kalıcı kısıt, Hetzner'in ~€4.5/ay'ı bile fazla). Yeni plan: **Oracle Cloud "Always Free" ARM** (VM.Standard.A1.Flex, 4 vCPU/24GB, aarch64) + **DuckDNS ücretsiz subdomain** + `docker-compose.prod.yml` ile deploy. Detay + Oracle'a özgü tuzaklar (VCN Security List, kapasite hataları) `DEPLOY.md`'de. Oracle hesap açılışında kart doğrulaması "Transaction Failed" veriyordu (TR bankalarının çoğu Oracle'ın yurt dışı doğrulama çekimini varsayılan engelliyor) — sonunda AWS köprüsüne geçildi, Oracle denemesi terk edildi.
2. **API dökümantasyon portalı** — Swagger/Redoc cila, demo API key, kullanım örnekleri, Postman collection. (Hâlâ bekliyor, bkz. CLAUDE.md yol haritası.)
3. **Launch içeriği** — landing son metinler, OG görselleri, Product Hunt materyali. (Hâlâ bekliyor.)
4. **README** — ✅ v1.10'da tüm proje geneli güncellendi.
5. **Gerçek Stripe entegrasyonu** — kod tarafı hazır; sadece gerçek hesap + `STRIPE_*` anahtarları + `stripe listen` webhook'u + `BILLING_DEV_MODE=false` gerekir. (Hâlâ bekliyor.) Kullanıcı dev modda tek tıkla tier değiştirmenin "bir şey değiştirmediğini" fark etti — bu KASITLI (dev-mode simülasyon, ödeme yok), gerçek kısıtlama ancak burada devreye girer.
6. ~~**KRİTİK — Tier-gating gerçek değil**~~ — ✅ **20 Temmuz 2026'da tamamlandı**: arama sonucu tavanı (Free 10/Pro 50/Enterprise 200), `/api/v1/news/{id}/related` (Pro+), `/ws/feed` (Pro+), `subscription_router.py`'deki `frequency=instant` (Pro+, e-posta→User tier eşlemesiyle) artık gerçekten kilitli. ~~"Ham veri export" hâlâ hiç yazılmamış~~ — ✅ **21 Temmuz 2026'da tamamlandı** (v1.16).
7. ~~**Dependabot kurulumu**~~ — ✅ **23 Temmuz 2026'da tamamlandı** (v1.18 commit'inde, `.github/dependabot.yml`): pip (kök dizin), npm (`/frontend`), github-actions ekosistemleri, üçü de haftalık Pazartesi taraması. Review/merge/rebuild kararı hâlâ kullanıcıda (bilinçli — otomatik merge/deploy yok). Bağımlılık güncellemesi geldiğinde unutulmaması gereken: Docker image REBUILD edilmeli, sadece `restart` yetmez.

**✅ v1.18 — Kafka→Redpanda + PWA + ücretsiz deploy hazırlığı (22 Temmuz 2026, kod tarafı tamamlandı, deploy sonradan AWS köprüsüyle tamamlandı):**
- **Neden:** Kullanıcı v2.0 deploy'a başlamak isteyince Hetzner CX22 bile ($0/ay kalıcı bütçe kısıtına göre) fazla bulundu — köklü bir plan değişikliği gerekti.
- **Kafka+Zookeeper → Redpanda** — Confluent'in Kafka+Zookeeper Docker imajları sadece amd64; gerçekten sonsuza dek ücretsiz güçlü sunucu Oracle Cloud Always Free ARM (aarch64) olduğu için imaj uyumsuzluğu doğdu. Redpanda Kafka wire-protokolünü konuşan tek-binary bir alternatif — `aiokafka` client kodu HİÇ değişmedi, sadece `docker-compose.yml`/`docker-compose.prod.yml`'de `zookeeper`+`kafka` servisleri silinip tek `redpanda` servisi eklendi. Değerlendirilip elenen alternatifler: Redis Streams (mevcut Redis'i kullanır ama `XADD`/`XREADGROUP`'a yeniden yazım ister), RabbitMQ (farklı protokol, en büyük yeniden yazım).
- **PWA (frontend, sıfırdan)** — `frontend/public/manifest.webmanifest`, `frontend/public/sw.js` (elle yazılmış minimal service worker, `next-pwa` KULLANILMADI), `frontend/components/ServiceWorkerRegistration.tsx`. İkonlar Pillow ile programatik "N" monogram olarak üretildi (matrix tema renkleri).
- **`DEPLOY.md` tamamen yeniden yazıldı** — Oracle Cloud Always Free ARM + DuckDNS. **Oracle'a özgü güvenlik duvarı tuzağı:** VCN Security List `ufw`'den AYRI ve ONA EK — ikisi de açılmadan port erişilemez kalır.
- **Dependabot kurulumu** — `.github/dependabot.yml` bu commit'te eklendi.
- **`/ws/feed` bağlantı limiti** — `WebSocketNotifier` artık per-user (`ws_max_connections_per_user`, varsayılan 5) + global (`ws_max_total_connections`, varsayılan 500) tavan uyguluyor. `can_accept(user_key)` router'da `accept()`'ten ÖNCE soruluyor.
- **Test:** 517 → 521.
- **KAPSAM DIŞI (bilinçli):** App Store/Play Store yok — sadece PWA.

**✅ v1.19 — public `/news/search` kota atlatma kapatıldı (23 Temmuz 2026, tamamlandı):**
- v1.17 denetiminde "ürün kararı" diye ertelenmişti: kimliksiz `/news/search` sadece IP-bazlı `30/dakika` ile korunuyordu, günlük tavan yoktu → teorik ~43k istek/gün.
- Çözüm: `@limiter.limit("30/minute;200/day")` (`news_router.py::search_news`).
- **Test deseni:** `limiter._route_limits["<module>.<func>"]` içindeki kayıtlı `Limit` nesneleri doğrudan denetlendi — **genel kural: slowapi ile korunan bir route'un limit DEĞERİNİ doğrulamak istediğinde, HTTP döngüsüyle tüketmek yerine `limiter._route_limits` üzerinden statik olarak oku.**
- **Test:** 521 → 522.

**✅ Redpanda migrasyonu GERÇEK container'larla ilk kez doğrulandı + iki altyapı bug'ı bulunup düzeltildi (23 Temmuz 2026, aynı oturum):**
- **Bulgu 1 — hayalet Kafka/Zookeeper container'ları:** compose dosyası v1.18'de değişmiş ama kimse `docker compose up -d` çalıştırmamıştı; Docker Desktop yeniden başlayınca `restart: unless-stopped` politikalı ESKİ container'ları diriltti. **Genel ders: bir compose dosyasını değiştirdikten sonra `docker compose down` çalıştırmadan bırakırsan, Docker Desktop bir sonraki açılışında ESKİ container'ları sessizce diriltebilir.**
- **Bulgu 2 — `hf-xet` indirme tıkanması:** `huggingface_hub` + `hf-xet` paketi Xet protokolünü kullanıyor, bu ortamda anlık kilitleniyordu. **Çözüm:** `HF_HUB_DISABLE_XET=1` env var'ı.
- **Sonuç:** Tam stack gerçek container'larla sıfırdan ayağa kaldırıldı ve sağlıklı çalıştığı doğrulandı.

**✅ v1.14 — Tier-gating gerçek yapıldı + canlı testte bulunan auth bug'ları (20 Temmuz 2026, tamamlandı):**
- **Tier-gating** — `TIER_SEARCH_RESULT_CAP` (Free 10/Pro 50/Enterprise 200) + `tier_at_least()`. `/api/v1/news/{id}/related` ve `/ws/feed` artık Pro+ ister.
- **WebSocket close code gotcha:** `accept()` ÇAĞIRMADAN `close(code=1008)` çağrılıyordu — Starlette `TestClient` doğru yakalıyor ama GERÇEK tarayıcı özel close code'u HİÇ GÖREMİYOR. **Genel kural: bir WebSocket route'unu reddederken `accept()` + hemen `close(code=...)` kullan.**
- **Canlı testte kullanıcının bulduğu 3 auth bug'ı:** (1) "[object Object]" hatası — `detail` bazen dizi dönebiliyordu, `extractErrorMessage()` eklendi. (2) Moderatör olmayan kullanıcı `/admin/users`'a gidince yanlışlıkla API key istiyordu. (3) `muz@muz.com` gibi mail almayan domainler kayıt oluyordu — `check_deliverability=True` eklendi.
- **Docker disk temizliği:** `docker builder prune` buildx cache'i temizlemiyor, `docker buildx prune -af` gerekiyor.

**✅ v1.15 — E-posta doğrulama akışı (21 Temmuz 2026, tamamlandı):**
- Kayıtta gönderilen onay linki, yumuşak+orta karma gating (sadece `/billing/checkout` `email_verified=true` ister).
- **Gotcha — Resend sandbox kısıtı:** doğrulanmış domain yoksa sadece hesap sahibinin KENDİ e-postasına gönderim yapılabiliyor.
- **Test kalıbı:** paylaşılan domain modeline yeni "varsayılanı kısıtlayıcı" alan eklerken TÜM test factory helper'larını tara.
- **Backend:** 494 test.

**✅ v1.17 — KAPSAMLI GÜVENLİK DENETİMİ + sertleştirme (21 Temmuz 2026, kritik/yüksek tamamı kapatıldı):**
5 eksende (auth/oturum, injection, secrets/altyapı, iş mantığı/DoS, bağımlılıklar) tam denetim — 34 kod/config bulgusu + 10 bağımlılık zafiyeti. Kritik 4 + Yüksek 9 = 13'ünün TAMAMI kapatıldı.
- 🔴 **EN KRİTİK — sızmış DB şifresi:** `.env` git geçmişinde açıktaydı VE hâlâ kullanımdaydı. Rotate edildi. **Ders: `.env`'i git'ten kaldırmak sızıntıyı çözmez — tek gerçek çözüm rotasyondur.**
- **Prod başlangıç guard'ı:** `_reject_unsafe_production_config` — `API_KEY`/`BILLING_DEV_MODE`/`CORS_ORIGINS`/`SESSION_COOKIE_SECURE` zayıfsa uygulama açılmayı reddeder.
- **Auth sertleştirme:** login/register rate limitsizdi → 15/dk. Timing-safe email enumeration koruması, `secrets.compare_digest`.
- **TOCTOU yarışı, gelir kaçağı (legacy `/news/{id}/related` tier kontrolsüzdü), e-posta HTML injection, rate limit boşlukları, root container'lar, bağımlılık güncellemeleri** — hepsi kapatıldı.
- **Test:** 505 → 517.

**✅ v1.16 — Ham veri export + dashboard canlı liste enjeksiyonu (21 Temmuz 2026, tamamlandı):**
- `GET /api/v1/news/export` — Enterprise-only, CSV+JSON, `EXPORT_MAX_ROWS` (20000), 10/dk rate limit.
- **Bug bulundu ve düzeltildi:** `entities` alanı hem CSV hem JSON'da string'e çevriliyordu — JSON'da yanlış. **Genel ders: aynı satır verisini birden fazla formata seren kodda format-özel dönüşümleri ortak satır üretici fonksiyondan AYRI tut.**
- **Backend:** 505 test.

**✅ Dashboard "Son Haberler" listesi WebSocket'ten canlı beslenmeye başladı (aynı oturum):**
- `LiveTicker` kendi bağlantısını tutuyordu ama asıl haber listesi WS'ten hiç güncellenmiyordu. `live-feed-context.tsx` ile tek bağlantı paylaşıma açıldı.

**✅ v1.12 kalan maddeleri: responsive + erişilebilirlik + tema perf profilleri (20 Temmuz 2026, tamamlandı):**
- **Responsive tarama:** birkaç sayfada CSS Grid blowout riski giderildi (`minmax(0,1fr)`).
- **Erişilebilirlik — kontrast:** `--text3` tokeni 9 temanın HEPSİNDE WCAG AA eşiğinin altındaydı, hesaplanıp düzeltildi. `--accent` kontrastı da temalar arası tutarsızdı, düzeltildi.
- **Erişilebilirlik — klavye/aria:** Escape ile dropdown kapatma, aria-* öznitelikleri, `LiveTicker` hover/focus'ta duruyor (WCAG 2.2.2).
- **Tema performans profilleri:** `perf: "low"|"high"`, canvas efektleri `density()` ile parçacık sayısını yarıya indiriyor.
- **Canlı testte bulunan 2 bug:** rozet satır kırıyordu (`.badge { white-space: nowrap }` eklendi), landing istatistik satırı dil değişiminde kayıyordu (`minWidth:160`).

**✅ WebSocket canlı ticker + landing/navbar UX düzeltmeleri (20 Temmuz 2026, tamamlandı):**
- `useLiveFeed.ts` + `LiveTicker.tsx` eklendi.
- **Landing "En Popüler" rozeti bug'ı:** `badge` + `gradient-text` class kombinasyonu metni tamamen transparan yapıyordu. **Genel kural: `badge` + `gradient-text` class'larını birlikte kullanma.**
- **Navbar scroll-yönüne duyarlı hale getirildi** — kök neden landing sayfasının kök `<div>`'indeki `overflowX:hidden` navbar'ın scroll container'ını bozuyordu. **Genel kural: `overflow-x`/`overflow-y`'yi sayfa kökünde değil, ihtiyaç duyan en dar kapsamlı elementte kullan.**

**✅ Admin müşteri paneli + rol hiyerarşisi (8 Temmuz 2026, tamamlandı):**
- `GET /admin/users` + `is_paying` alanı. v1.13 rol hiyerarşisi (user < moderator < admin) — boolean `is_admin` kaldırıldı, `users.role` (VARCHAR) geldi.

**✅ Sponsor tekillik kuralı + email i18n refactor + digest kişiselleştirme (8 Temmuz 2026, tamamlandı):**
- **Sponsor bug'ı:** `create_sponsor` diğer sponsorları pasife almıyordu, aynı anda 4 sponsor aktif olabiliyordu.
- **email_adapter.py sözlük tabanlı i18n'e geçti** — `if language=="TR" else` dallanması SOLID/Open-Closed ihlaliydi, bu artık projedeki TÜM yeni kod için genel kural.
- **Günlük digest gerçekten kişiselleşti** — `subscriber_matching.py` paylaşımlı domain fonksiyonu.

**✅ Go-live hazırlık turu (8 Temmuz 2026, tamamlandı):**
Temel SEO (generateMetadata, robots.ts, sitemap.ts), `/privacy`+`/terms`, nginx `/api/v1/` prefix-korumalı location bloğu + WebSocket header'ları (bu WS header eklemesi go-live turunda yapılmıştı — sonradan v2.1.1'de `websockets` paketinin hiç pinlenmemiş olması nedeniyle bu header'lar ASGI seviyesinde işe yaramadığı ortaya çıktı), `frontend/lib/api.ts::BASE` export edildi, landing sayfasına canlı semantik arama demosu.

---

## TAMAMLANAN MİLESTONE'LAR (v1.18 → v2.6, 19–27 Ağustos 2026)

`CLAUDE.md` 18 Ağustos'ta bu dosyaya ayrıştırıldıktan sonra biriken bir haftalık
yoğun geliştirme — roadmap'in ✅ işaretli maddelerinin tam anlatısı burada,
`CLAUDE.md`'de sadece 1-2 satırlık pointer'lar kaldı.

**✅ Hesap silme endpoint'i (19 Ağu 2026, tamamlandı):**
`DELETE /account` — parola + checkbox onayı, owner rolü hariç, Stripe
aboneliği varsa otomatik iptal, ilişkili tüm satırlar (sessions/token'lar/
usage_log/bülten aboneliği) kalıcı silinir. Frontend'de /account sayfasında
"Tehlikeli Bölge".

**✅ Kullanıcı banlama — moderatör/admin (19 Ağu 2026, tamamlandı):**
`PATCH /admin/users/{id}/active` — `update_user_role` ile birebir aynı
kademeli yetki deseni (hedefin rolü actor'dan kesinlikle düşük olmalı, owner
hiç hedef olamaz, kendi kendini banlayamazsın), banlarken
`delete_sessions_for_user` ile tüm oturumlar da düşürülür. Admin panelinde
durum sütununda Banla/Banı Kaldır butonu.

**✅ Rakip taraması sonrası quick-win paketi (19 Ağu 2026, canlıya deploy edildi ve SSM üzerinden uçtan uca doğrulandı):**
Ground News/Feedly/Inoreader/FreshRSS taraması (detay için scratchpad'deki
araştırma raporuna bak). Kaydet/sonra oku (`/account/saved`, v2.2), kaynak
"corroboration" rozeti (veri zaten vardı, sadece UI'a eklendi), tarayıcı-yerel
TTS (Web Speech API). Okuma süresi tahmini 20 Ağu 2026'da KALDIRILDI (bkz.
roadmap madde 18 — gerçek makale metni hiç çekilmediği için yanıltıcıydı).

**✅ Story cluster görünümü (19 Ağu 2026, tamamlandı):**
"Bu haberi kim nasıl anlatıyor" — `GET /news/{id}/sources` +
`/api/v1/news/{id}/sources` (tier gating yok, herkese açık — corroboration
rozeti gibi şeffaflık özelliği). `ChromaSearchRepository.find_similar` zaten
indexlenmiş embedding'i tekrar hesaplamadan (`collection.get`) benzerlik
araması yapıyor, dedup eşiğinden (0.92) daha gevşek bir eşikle (0.72) aynı
olayı farklı kaynakların anlattığı makaleleri yakalıyor. `NewsService.
get_story_cluster` orkestrasyon, `NewsCard`'da kart footer'ında
"🔗 Kaynaklar" toggle'ı.

**✅ Arama ilişkisel sorgu genişletme — query expansion (20 Ağu 2026, tamamlandı):**
"İstanbul" araması "Beykoz" gibi ilişkili haberleri de düşük skorla yakalasın
diye Groq'a `QueryExpansionPort` (`GroqQueryExpander`, cache'li
`CachingQueryExpander`) üzerinden ikincil terim üretiliyor; `NewsService.
hybrid_search` bunu `_keyword_relevance`'a `secondary_terms` olarak geçiyor,
tamamen fail-open (Groq başarısız olursa eski davranış aynen sürer).
`SEARCH_QUERY_EXPANSION_ENABLED` ile açık/kapalı. `get_news_service` DI'da
`build_query_expander(get_cache())` ile bağlandı.

**✅ "Kaynaklar" (story cluster) UI'ının kullanışlılığı (24 Ağu 2026, çözüldü):**
Canlı veriyle test edilince kullanıcının şikayeti hem UI hem kod tarafında
doğrulandı: (1) panel gerçekten İlgili Haberler'in görsel bir kopyasıydı
(aynı kart stili) — kaynak adına göre tekilleştirilmiş rozet/pill satırına
çevrildi (`NewsCard.tsx`); (2) "tam çalışmıyor" algısının arkasında GERÇEK
bir skorlama bug'ı vardı — bkz. `CLAUDE.md` BİLİNEN NOTLAR'daki "jenerik
entity" maddesi. `_find_corroborating_articles` düzeltildi, 2 regresyon
testi eklendi (746 test yeşil). **Aynı gün içinde kullanıcı "başka yerde de
aynı bug olabilir mi" diye sorunca tarama genişletildi**, `get_related`
(Pro+ ücretli özellik) VE `get_story_cluster`'ın semantik tarafında da aynı
bug sınıfı bulunup düzeltildi (PR #50, +7 test, 751 test yeşil).

**✅ Deploy pipeline'ı main merge'ine bağla (24-25 Ağu 2026, iki aşamada TAMAMEN çözüldü):**
24 Ağu: prod artık ayrı bir dal (`optimize/t3-small-ram`) yerine doğrudan
`main`'den deploy ediliyor — drift kaynağı ortadan kalktı (PR #48/#47 main'e
merge edilmişti ama prod hâlâ eski daldan deploy ediliyordu, `groq_query_
expander.py` prod'da hiç yoktu). 25 Ağu: `.github/workflows/tests.yml`'e
main'e her push'ta (test+frontend geçerse) SSM üzerinden otomatik redeploy +
`/api/health` doğrulaması yapan bir `deploy` job'ı eklendi (PR #52), kullanıcı
gerekli iki GitHub Secret'ı ekledi, `gh run rerun --failed` ile uçtan uca
doğrulandı (otomasyon gerçekten kendi başına SSM'e bağlanıp deploy yaptı).
Artık main'e her merge tam otomatik prod'a çıkıyor — elle SSM adımı sadece
manuel müdahale/debug için saklı kaldı.

**✅ Analytics/hata takibi — Sentry + PostHog (25 Ağu 2026, AKTİVE edildi ve canlıda doğrulandı):**
Sentry hem `app` hem `worker`'da `environment=production` etiketiyle event
gönderiyor, PostHog EU host'a bağlı, key frontend bundle'ına gömülü. Her
ikisi de SaaS ücretsiz katman — VPS'e yeni bir servis/RAM eklemiyor (self-host
GlitchTip/Umami gibi seçenekler bilinçli olarak elendi).
- **Sentry:** `src/infrastructure/observability/sentry.py::init_sentry()` —
  `SENTRY_DSN` boşsa tamamen no-op, kurulum kendi içinde try/except'li. 3 yeni test.
- **PostHog:** `frontend/components/AnalyticsProvider.tsx` — App Router
  pageview'larını `usePathname` ile elle gönderir (`useSearchParams` DEĞİL —
  Suspense gerektirir), autocapture açık.
- `/privacy` sayfası (TR+EN) güncellendi — eskiden "takip/reklam çerezi
  kullanılmıyor" diye kesin bir iddiası vardı, PostHog/Sentry'nin varlığı ve
  reklam amaçlı KULLANILMADIĞI açıkça belirtildi.
- Kullanıcı Sentry (DE region) + PostHog (EU Cloud —
  `NEXT_PUBLIC_POSTHOG_HOST=https://eu.i.posthog.com` şart, `us.` varsayılanı
  çalışmaz) hesabı açtı, `docker compose up --build -d` ile aktive etti
  (PostHog key build-time ARG olduğu için frontend REBUILD gerekiyor).
  **Frontend Sentry (Next.js SDK) bilinçli olarak YAPILMADI** — backend zaten
  kapsıyor, `next.config.js`'e dokunup build'i kırma riski taşıyordu.

**✅ Web Push bildirimleri — breaking news (25 Ağu 2026, tamamlandı):**
Spec: `docs/superpowers/specs/2026-08-25-web-push-bildirimleri-design.md`,
plan: `docs/superpowers/plans/2026-08-25-web-push-bildirimleri.md`,
worktree'de inline uygulandı, subagent kullanılmadı. Mevcut "Anlık Uyarılar"
(instant) e-posta aboneliğinin AYNI keyword eşleşmesini ikinci bir kanal
olarak paylaşıyor — ayrı bir "breaking news" kavramı icat edilmedi. Yeni
`WebPushPort` + `PyWebPushAdapter` (pywebpush + VAPID) +
`PushSubscriptionRepositoryPort` — isim bilinçli olarak `NotificationPort`
(mevcut, `/ws/feed` için) ile çakışmasın diye farklı seçildi. Pro+ gating +
giriş zorunlu. VAPID anahtarları `npx web-push generate-vapid-keys` ile
üretildi (3. parti hesap gerekmiyor). **Otomatik güvenlik incelemesi bir IDOR
bulup düzeltti:** `DELETE /account/push-subscription` endpoint sahipliğini
hiç doğrulamıyordu — düzeltildi, artık sadece `current_user.email`'e ait
abonelikler silinebiliyor.

**✅ Admin panelinde /admin/users tablosu sıralanabilir (26 Ağu 2026, tamamlandı):**
Sahibinden.com tarzı: sütun başlığına (ekstra buton yok) tıklayınca
sıralanır. 3 durumlu döngü (`frontend/app/admin/users/page.tsx::handleSort`):
1. tık = artan, 2. tık = azalan, 3. tık = varsayılana döner — `users` state'i
hiç mutasyona uğramıyor, `displayedUsers` bir `useMemo` ile türetiliyor. Rol
ve Tier sütunları bilinçli olarak alfabetik değil RANK'e göre sıralanıyor.
Bounded bir frontend işi, backend değişikliği gerekmedi.

**✅ Test paketi sağlık denetimi (25 Ağu 2026, yapıldı — sonuç: paket sağlıklı, temizlik gerekmedi):**
AST tabanlı bir tarama (751 test fonksiyonu) 3 soruyu kontrol etti: (1)
**Ölü/orphan test yok** — tüm `from src....` import'ları gerçek modüllere
çözülüyor. (2) **Skip/xfail/TODO/FIXME işaretli 0 test.** (3) **"Mock'un
kendisini test etme" şüphesi incelendi:** ilk kaba tarama 62 "şüpheli"
işaretledi ama çoğu `pytest.raises(...)`/`mock.assert_called_with(...)` gibi
gerçek doğrulama yapan kalıplardı (metodoloji düzeltildi). Gerçek aday
sadece 9'a indi, hepsi incelendi — hepsi bilinçli "exception fırlatmamalı"
testleri, projenin "Exception'ları yut, logla, fallback dön" felsefesiyle
birebir örtüşüyor.

**✅ RAG tabanlı "bu konuda soru sor" mini sohbet (26 Ağu 2026, canlıya çıktı):**
Spec: `docs/superpowers/specs/2026-08-26-rag-soru-cevap-design.md`, plan:
`docs/superpowers/plans/2026-08-26-rag-soru-cevap.md`, 13 görev, inline TDD
ile uygulandı, subagent kullanılmadı. `QuestionAnsweringPort`
(`GroqQuestionAnswerer`, `AnalysisPort`'tan AYRI — `QueryExpansionPort` ile
aynı gerekçe) + kanıt kapısı deterministik kodda çözülüyor (retrieval skoru
`RAG_RETRIEVAL_THRESHOLD` altındaysa Groq'a hiç gidilmiyor) + soru başına en
fazla 1 Groq çağrısı. Endpoint bilinçli olarak sadece `/api/v1/news/ask`'te
(legacy router'a EKLENMEDİ) — `usage_tracking_middleware` sadece `/api/v1/`
path'lerini kota sayacına işliyor, spec bunu fark etmemişti, brainstorming'de
düzeltildi. Frontend: `/dashboard/ask` (genel + habere-özel tamamen ayrı
sohbet oturumları, kalıcı saklama yok), `NewsCard`'da "💬 Sor" butonu,
`/account?prefillKeyword=` ile "haberdar et" akışı. PR #70 (önce bağımsız bir
keyword-alert substring bug'ı + hesap sayfası chip UI'ı), #71 (RAG'ın
kendisi), #72 (canlı QA'da bulunan fail-fast hotfix'i).

**✅ Haber akışı kümelenmesi + RAG tarih-farkındalığı + worker starvation (31 Ağu 2026, PR #77/#78):**
Kullanıcı canlıda iki sorun bildirdi: haberlerin sürekli aynı kaynaktan arka
arkaya gelmesi, ve RAG'ın "gram altın haftaya nasıl başladı" sorusunda güncel
değil bir hafta önceki habere göre cevap vermesi. Kapsamlı SSM canlı
diagnostiğiyle (worker log analizi, 300 satırlık DB run-length sıralama
testi, container içi `hybrid_search`/`answer_question` çağrıları, RSS feed
curl doğrulaması) araştırıldı, TDD ile 5 düzeltme yapıldı:

- **PR #77 (4 düzeltme):**
  1. Groq TPM tavanına yakınken 429'u beklemeden proaktif throttle
     (`groq_analyzer.py`, `x-ratelimit-remaining-tokens`/`reset-tokens`
     header'larını okuyor).
  2. Ana akış artık `created_at` değil `published_at`'e (coalesce ile) göre
     sıralanıyor (`news_repository.py`) — 300 haberlik canlı örneklemde 0
     sıralama ihlali doğrulandı (öncesi 20-25+ aynı-kaynak dizisi, sonrası
     en uzun dizi 6).
  3. CNN Türk RSS URL'i güncellendi — eski adres 1 Temmuz'dan beri kaynağın
     kendi tarafında donmuştu.
  4. RAG prompt'una bugünün tarihi + "birden fazla kanıt aynı konuyu farklı
     tarihlerde anlatıyorsa EN YENİSİNİ esas al" kuralı eklendi
     (`rag_common.py`/`groq_question_answerer.py`).
- **PR #78 (asıl kök sebep, ayrı bir oturum turunda bulundu):** worker
  (`kafka_consumer.py`) kaynakları SIRAYLA ve bir kaynağın TÜM yeni
  haberlerini bitirmeden bir sonrakine geçmeden işliyordu — Groq rate limit
  ağırlaşınca TRT Haber (registry'de 1. sırada, yoğun kaynak) worker'ı
  SAATLERCE kilitleyip CNN Türk (6. sırada) dahil diğer 16 kaynağı aç
  bırakabiliyordu (canlıda 40 dakika boyunca SADECE TRT Haber işlendiği
  doğrulandı). `NewsService.update_news_from_source`'a `max_new_articles`
  parametresi + yeni ayar `worker_max_new_articles_per_run` (varsayılan 5)
  eklendi — kaynak başına çalıştırma başına en fazla N yeni haber işlenir,
  kalanlar dedup'ta hâlâ "yeni" göründüğü için bir sonraki taramada devam
  eder.

**Kalıcı, bilinçli olarak bugün çözülmeyen bulgu:** proaktif TPM throttle
bekleme sürelerini başlangıçta kısalttı (430-520s → 73-237s) ama 40 dakikalık
gözlemde tekrar eski seviyeye (420-439s) tırmandı ve hiç tetiklenmedi (0/10
olay) — asıl kısıtın TPM değil **TPD (günlük) kota** olduğu ortaya çıktı:
günlük ~206 haberlik hacim `gpt-oss-20b`'nin 200K TPD tavanına zaten çok
yakın/üstünde. Kullanıcı isteğiyle sıradaki oturumun İLK gündem maddesi
olarak not düşüldü (`CLAUDE.md` YOL HARİTASI madde 25) — iki olası kol:
haber başına token maliyetini düşürmek ya da günlük analiz hacmini
düşürmek.

İki PR de TDD ile inline (subagent'sız) yapıldı, merge+deploy edildi
(GitHub Actions otomatik SSM deploy job'ı ile, health check dahil
doğrulandı). 849/849 test yeşil.

**✅ Groq TPD maliyeti — 1. dilim (31 Ağu 2026, aynı gün sonraki oturum, PR #79):**
Yukarıdaki madde 25'in "önce ölç, sonra karar ver" seçeneğiyle ele alındı.
Statik/analitik ölçüm (prompt+`max_tokens` tahmini) kayıtlı gerçek ölçümle
(199.555/200.000, ~206 haber/gün → ~969 token/haber) çapraz doğrulandı —
canlıya dokunmadan, SSM diagnostiği gerekmeden. Bulgular: (1) `GroqQuery
Expander`/`GroqQuestionAnswerer` zaten 120b'ye taşınmış (roadmap #24
notu eskimişti, düzeltildi) — 20b TPD havuzunun tek tüketicisi artık worker'ın
haber analiz hattı; (2) `text[:1000]` kırpması gerçek RSS teaser boyutları
(~30-80 kelime) nedeniyle neredeyse hiç devreye girmiyor, elendi; (3)
`is_near_duplicate` kontrolü Groq analizinden SONRA çalışıyor — near-duplicate
haberler bile tam analiz alıyor, gerçek bir israf ama `is_duplicate` feed'i
filtrelemediği için düzeltmek ürün kararı gerektiriyor, bugün kapsam dışı.
**Uygulanan güvenli dilim:** `common.py::build_analysis_prompt` şablonu
~278→~192 token'a sıkıştırıldı (aynı alan sözleşmesi + kalibrasyon örnekleri,
haber başına ~86 token/~%9 TPD kazancı) + Groq'un gerçek `usage.prompt_
tokens`/`completion_tokens` alanı `nexstream_groq_tokens_total` metriğine
işlenmeye başladı (`groq_analyzer.py::_record_token_usage`) — bir sonraki
karar artık tahmine değil bu metriğe dayanabilir. 7 yeni test (856/856
yeşil), TDD ile inline (subagent'sız) yapıldı, merge+deploy+health check
doğrulandı.

**✅ Arama skoru yeniden tasarımı + görünür güven rozeti (31 Ağu 2026, aynı gün
üçüncü oturum, PR #80):** 27 Ağu 2026'da yazılan planın uygulanması —
`superpowers:executing-plans` ile inline (subagent'sız), 6 task TDD.
`compute_trust_score` (saf domain fonksiyonu, `domain/scoring/trust.py`,
%35 quality + %45 credibility + %20 corroboration, `or 0.5` DEĞİL `is not
None` kontrolü) + `Article.trust_score`/`NewsResponse.trust_score` property'si
+ `NewsService._distinguishing_query_terms`/`_grounding_factor` (sorgudaki
büyük harfli kelimeler özel isim adayı sayılır, adayda literal geçmiyorsa
×0.3 ceza — cümle başı DAHİL, çünkü bu uygulamadaki sorgular konu-önce
yazılıyor) + `hybrid_search`'e grounding+credibility+trust_score entegrasyonu
+ `get_story_cluster` kaynaklarına trust_score + `NewsCard`'da görünür güven
rozeti (eski quality-only rozetin yerine, hover'da yüzde breakdown'ı).

Bu, 24 Ağu 2026'daki "jenerik entity" bug sınıfının (ingest-zamanı entity-
overlap) RAG/arama retrieval'daki SORGU-zamanı görünümünü kapatıyor — dünkü
"Beşiktaş maçı saati" örneğinde "Filenin Sultanları, Almanya karşısında!"
gibi alakasız ama "maç" temasıyla semantik benzeyen içerikler artık
grounding cezasıyla geriye düşüyor.

**Uygulama sırasında planın öngörmediği 3 gerçek bulgu çıktı, tam test
paketi çalıştırılınca ortaya çıktı, hepsi düzeltildi:**
1. `NewsResponse.trust_score` eklenmesi `/api/v1/news/export` CSV yolunu
   kırdı — `_EXPORT_FIELDS` listesi (`csv.DictWriter(extrasaction="raise")`
   ile kullanılıyor) yeni alanla senkron değildi, eklendi.
2. Planın Task 5'i `test_news_service.py`'yi hedefliyordu ama
   `get_story_cluster` testleri gerçekte ayrı bir dosyada
   (`test_story_cluster.py`) yaşıyordu — 4 mevcut test tam-dict eşitliği
   yaptığı için trust_score alanıyla güncellendi. Biri ayrıca semantik
   olarak değişti: "hedefin entity'si yoksa `get_articles_by_ids` hiç
   çağrılmamalı" iddiası artık geçersizdi (entity doğrulaması için değil
   ama trust_score için TAM BİR KEZ çağrılıyor), assertion buna göre
   güncellendi.
3. Plan'ın bir testi (`no_distinguishing_term_leaves_ranking_unchanged`)
   `published_at=None` kullanıyordu — bu, `_decay_factor`'ü recency=0 için
   floor'a (0.5) düşürüyor, testin İZOLE etmek istediği grounding/
   credibility sinyalinden bağımsız bir etki katıyordu. Gerçekçi bir
   `published_at` (şimdi) ile decay=1.0'a sabitlendi, testin amacına
   (SADECE grounding+credibility'yi izole etmek) geri döndürüldü.

Ayrıca 8 mevcut `hybrid_search` skor-sabiti testi `credibility_factor=0.85`
(credibility_score=None varsayılanı, `0.7+0.3*0.5`) yansıtacak şekilde
güncellendi — sıralama/davranış BİREBİR aynı kaldı, sadece mutlak skor
sayısı küçüldü (regresyon değil, plan'ın öngördüğü davranış).

Backend test sayısı 856→881 (+25), 881/881 yeşil, frontend `tsc --noEmit` +
`next build` temiz. Eski
`feature/arama-skoru-ve-guven-rozeti` dalı (27 Ağu'dan kalma, main
2bcdc60'tan çok geride, main'e merge edilmiş her şeyi geri alırdı)
ARTIK GEREKSİZDİ — gerçek değeri (spec/plan/SMTP fix/RAG content fix)
zaten main'e ayrı yoldan geçmişti, doğrulanıp silinmeden bırakıldı (Bash
classifier `git branch -D`'yi engelledi), yeni iş temiz bir dal
(`feature/arama-skoru-ve-guven-rozeti-v2`) üzerinde yapıldı. Tam döngü
(TDD ile inline → PR #80 → CI yeşil → kullanıcı onayı → squash-merge →
otomatik SSM deploy → health check) uçtan uca doğrulandı.

**✅ Güven rozeti hover'ında gerçek puan dökümü (31 Ağu 2026, aynı gün PR
#80'in hemen ardından, PR #81):** kullanıcı geri bildirimi — rozetin hover
metni HER haberde AYNI statik yüzdeleri yazıyordu ("%45 kaynak
güvenilirliği, %35 içerik kalitesi, %20 çoklu kaynak doğrulaması"), o
haberin GERÇEKTEN kaç puan aldığını göstermiyordu. `domain/scoring/
trust.py::trust_score_breakdown()` eklendi — quality/credibility/
corroboration'ın 100 puanlık toplama kaç kattığını ayrı ayrı döner (tek
doğruluk kaynağı). `compute_trust_score` artık bu üç parçanın TOPLAMI
(`round(sum)` DEĞİL `sum(round(parça))`) — kullanıcı hover'daki 3 sayıyı
elle toplasa kartın üstündeki toplam sayıyla HER ZAMAN eşleşsin diye
bilinçli tercih (aksi halde ±1 tutarsızlık riski vardı). `Article.
trust_breakdown` property + `NewsResponse.trust_breakdown` (nested
`TrustBreakdown` şeması) + CSV export'ta `entities` ile aynı desen (JSON
string'e çevrilir). Frontend'de `trustScoreText` artık gerçek dökümü
gösteriyor: "71/100 — Kaynak güvenilirliği: 40/45, İçerik kalitesi: 25/35,
Çoklu kaynak doğrulaması: 6/20" — breakdown eksikse (deploy öncesi
cache'lenmiş eski bir yanıt) eski statik metne düşülür, kart kırılmaz.
5 yeni test, 886/886 yeşil.

**Oturum içi bir hata da bu PR'da düzeltildi:** PR #80 merge edilip deploy
doğrulandıktan sonra `git checkout main` yapılmıştı (deploy'u izlemek için)
— hemen ardından bu yeni istek geldiğinde branch açmak unutulup 2 commit
doğrudan `main`'e atıldı. Fark edilince (henüz push edilmemişti, tamamen
geri alınabilirdi) `git branch <yeni-dal> HEAD` + `git branch -f main
origin/main` ile temiz şekilde düzeltildi — main hiç etkilenmedi. Ders
CLAUDE.md BİLİNEN NOTLAR'a işlendi.

**✅ RAG canlı QA'sında 6 gerçek bug bulunup düzeltildi (27 Ağu 2026, PR #73/#74/#75):**
Kullanıcı gerçek canlı QA'ya başladı (Docker yine kapalıydı, tarayıcıda canlı
siteyle test edildi):
1. E-posta/push keyword alert'te "altın" (gold) kökü "altında"/"altındaki"
   ("alt" [under] kelimesinin çekimi) ile harf düzeyinde çakışıyordu —
   `_FALSE_FRIEND_WORDS` istisnasıyla çözüldü.
2. RAG "soru sor" Groq'un paylaşımlı TPD kotası dolduğu için sürekli 503
   dönüyordu — `GroqQuestionAnswerer` + `GroqQueryExpander` ayrı modele
   (`gpt-oss-120b`) taşındı ("LLM modülü bölme" spike'ı bu vesileyle cevaplandı).
3. Kanıt-yok şablonu TR sitede aksansız Türkçe soruda İngilizce geliyordu —
   `AskRequest.language` eklendi, frontend'in kesin bildiği arayüz dili
   karakter-sezgisinden ÖNCE kullanılıyor artık.
4. `RETRIEVAL_THRESHOLD` 0.5→0.4: gerçekten ilgili bir haber (%46 skor) eşik
   yüzünden reddediliyordu — ilk gerçek kalibrasyon verisi.
5. "Haberdar et" önerisi sohbetin SON mesajını (takip sorusu, konu
   taşımayabilir) değil İLK mesajını kullanacak şekilde düzeltildi.
6. Python'un `.lower()`'ı Türkçe büyük "İ"yi bozup (`\b`-anchor kaçıyordu,
   "İsrailli" başlığı "israil" sorgusuyla hiç eşleşmiyordu) + doğal dilli
   sorulardaki soru parçacıkları ("mı", "kim", "nedir") coverage bölenini
   şişirip skoru yapay düşürüyordu — ikisi de düzeltildi (`_lower_tr_safe` +
   `_TR_QUESTION_STOPWORDS`).

**✅ LLM modüllerini bölme fizibilitesi — spike (27 Ağu 2026, CEVAPLANDI):**
Resmi Groq rate-limit dokümanı (model tablosunda her model FARKLI bir TPD
sayısıyla listeleniyor, ör. `openai/gpt-oss-20b`/`120b` 200K,
`qwen/qwen3.8-27b` 2M) VE canlı bir ampirik test (aynı anahtarla iki farklı
modele art arda istek atılıp `x-ratelimit-remaining-requests` header'ının
HER model için BAĞIMSIZ azaldığı gözlemlendi) TPD kotasının **MODEL BAŞINA
ayrı bir havuz** olduğunu kesinleştirdi. Sonuç: farklı bir SAĞLAYICIYA
geçmeye gerek yok — aynı Groq hesabında farklı bir MODEL seçmek bile
bağımsız bir kota açıyor. `GroqQuestionAnswerer` bu bilgiyle
`openai/gpt-oss-20b`'den (GroqAnalyzer/worker ile paylaşılan, neredeyse
sürekli dolu havuz) `openai/gpt-oss-120b`'ye taşındı — aynı gpt-oss ailesinde
kalındığı için JSON-güvenli, canlı bir istekle doğrulandı. Bu canlıda gerçek
bir bug'ı çözdü: worker'ın sürekli tükettiği paylaşımlı 20b havuzu RAG'a pay
bırakmıyordu, 26-27 Ağu arasında `/api/v1/news/ask` 3 ayrı kez 429→503 ile
"Şu an yanıt üretemiyorum" dönmüştü.

**✅ Stratejik "buzdağı" değerlendirmesi (24 Ağu 2026, yapıldı):**
Kullanıcı "dünyaya bakıp rasyonel sıralasak" dedi, gerçek web araştırması
(SaaS PMF aşamaları, 2026'nın AI/haber-toplama hukuki iklimi) + projenin tam
durumu temel alınarak bir Artifact hazırlandı (kullanıcının kendi Artifacts
galerisinde, "Buzdağının Neresindeyiz?" başlığıyla). Ortaya çıkan asıl soru
roadmap'te bir madde değil, bir FORK'tu: proje bilinçli olarak "bitmiş bir
portfolyo parçası" olarak mı bırakılacak, yoksa gerçekten kullanıcı
bulunmaya çalışılan bir ürüne mi dönüştürülecek? **Karar (aynı gün):** proje
ŞİMDİLİK bilinçli olarak portfolyo olarak kalıyor (bkz. `CLAUDE.md` MEVCUT
DURUM "Hedef" satırı) — AWS kredisi tükenmeden önce (~Kasım 2026 ortası)
tekrar gözden geçirilecek.

### Kasıtlı Kapsam Dışı (fayda/maliyet uygun değil)
K8s/Helm, Qdrant migration, CQRS, NTV Playwright scraper, Twitter/X entegrasyonu, custom (Stripe dışı) billing portalı, App Store/Play Store (sadece PWA)

---

## PRODUCTION DEPLOYMENT NOTLARI — ilk deployment tarihçesi (v1.6+)

Güncel/canlı deployment komutları için `CLAUDE.md`'nin "PRODUCTION DEPLOYMENT
NOTLARI" bölümüne bak. Burada sadece ilk kurulumun tarihsel adımları:

1. VPS'e (DigitalOcean/Hetzner/Oracle Free) Docker + Docker Compose kurulur
2. `.env` dosyası production değerlerle oluşturulur (`API_KEY`, `GRAFANA_PASSWORD` güçlü değerler)
3. SSL sertifikası: `infra/nginx/ssl/` dizinine self-signed cert koy, sonra certbot ile değiştir
4. `docker-compose -f docker-compose.prod.yml up -d`
5. Certbot ilk çalıştırma: `docker-compose -f docker-compose.prod.yml exec certbot certbot certonly --webroot -w /var/www/certbot -d your-domain.com`
