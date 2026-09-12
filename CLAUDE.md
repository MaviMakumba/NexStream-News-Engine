# NexStream News Engine — CLAUDE.md

Bu dosya Claude Code için proje bağlamını sağlar — GÜNCEL/canlı referans (mimari,
kararlar, durum, kurallar, komutlar, kalıcı gotcha'lar). Her session başında oku,
sonra gerekli dosyaları kendin aç.

**Kronolojik geliştirme tarihçesi (hangi sürümde ne yapıldı, hangi bug nasıl
bulunup düzeltildi, forensic "nasıl bulundu" detayları) `docs/CHANGELOG.md`'de**
— 18 Ağustos 2026'da bu dosya ~700 satıra ulaşınca, 8 Eylül 2026'da tekrar
~575 satıra (ve çok daha yoğun bir yazımla) ulaşınca oraya ayrıştırıldı.
**Kural:** CLAUDE.md sadece "şu an doğru olan / her oturumda gerekli olan"ı
tutar — bir madde geçmiş zamanlı bir olay anlatıyorsa (ne zaman, nasıl bulundu,
hangi PR) CHANGELOG'a, sadece "bundan sonra böyle yap" kuralı burada kalır.
Session başında okunması gerekmez, sadece "bu neden böyle yapılmış" sorusuna
cevap ararken aç.

---

## MİMARİ

Hexagonal (Ports & Adapters) mimari. Domain katmanı hiçbir dış bağımlılık bilmez.
Bağımlılık yönü: Adapter → Application → Domain. Tersi yasak.

Üst düzey: `src/{domain,application,adapters,infrastructure}` (hexagonal katmanlar,
+ `dependencies.py`/`main.py`), `migrations/`, `frontend/` (Next.js), `tests/`,
`infra/` (nginx/prometheus/grafana/loki/backup). Tam ağaç `ls`/`find` ile veya
dosyayı açarak görülür — burada tekrar edilmiyor.

Ağaçtan koda bakarak çıkarılamayan birkaç gerçek uyarı:
- `question_answering_port.py`'deki `QuestionAnsweringPort`, `AnalysisPort`'tan
  BİLİNÇLİ olarak AYRI (v2.6) — birleştirilmemeli.
- `web_push_port.py`'deki `WebPushPort`, var olan `NotificationPort` ile
  KARIŞTIRILMAMALI (v2.5, farklı amaç: VAPID push vs. genel bildirim).
- `POST /api/v1/news/ask` (RAG soru-cevap) bilinçli olarak SADECE v1 router'da —
  legacy router'a eklenmedi (v2.6).

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

**Yeni bir servis eklerken `restart: always` UNUTMA** — eklenmezse container
crash'ten kendini toparlar ama host REBOOT'unda hiç geri gelmez (normal
container-crash testleri bunu yakalamaz, sadece gerçek reboot ortaya çıkarır;
2 Eyl 2026'da certbot'ta böyle bulundu — detay CHANGELOG).

---

## KRİTİK KARARLAR VE GEREKÇELERİ

**Neden Groq?** Gemini'den taşındı. 14.400 req/gün ücretsiz, requests kütüphanesi yeterli (SDK yok). Rate limit: `Retry-After` header kullanılıyor. v1.5'ten itibaren tek prompt'ta sentiment + entities + topic çıkarılıyor. **Model: `openai/gpt-oss-20b`** (18 Ağu 2026'da `llama-3.1-8b-instant`'tan değişti — Groq o modeli tamamen kaldırdı). `reasoning_effort="low"` + `max_tokens=600` (reasoning modeli, `message.reasoning` alanı `content`'ten ayrı döner — JSON parse'ı bozmuyor). **Groq'un model listesi zamanla değişiyor/modeller kaldırılıyor** — `GET https://api.groq.com/openai/v1/models` ile periyodik kontrol faydalı; 404 + `model_not_found` görürsen model kaldırılmış demektir (rate limit/kota DEĞİL).

**Neden sentence-transformers?** Groq'un embedding API'si yok. `paraphrase-multilingual-MiniLM-L12-v2` modeli TR+EN destekler, tamamen local çalışır, API key gerektirmez. Kurulu versiyon: 3.3.1, torch: 2.10.0 (CPU wheel).

**Neden ayrı bir `embedder` servisi? (v2.0)** `app` ve `worker` modeli AYRI AYRI RAM'e yüklüyordu — t3.small'ın (1.9GB) kaldıramayacağı ~600MB'lık israf. Model artık tek bir serviste duruyor, ikisi de `HttpEmbedderAdapter` ile HTTP'den soruyor. **Domain katmanı hiç değişmedi** — mevcut `EmbeddingPort` soyutlaması aynen kullanıldı, hexagonal mimarinin karşılığını verdiği yer tam olarak burası. Yan kazanç: `app`/`worker` image'larında torch YOK (1.55GB → 516MB) ve `app` 1-2 dakika yerine ~6 saniyede healthy oluyor.

**Neden `chromadb-client`? (v2.0)** Kod yalnızca `chromadb.HttpClient` kullanıyor ama tam sunucu paketi kuruluydu (onnxruntime, tokenizers, opentelemetry, kubernetes client...). Kurulu versiyon: `chromadb-client` 1.5.5; sunucu imajı `chromadb/chroma:1.5.9` (= chroma sunucu 1.4.4). **DİKKAT:** imaj etiket numarası sunucu sürümünü YANSITMIYOR — `:1.5.5` etiketi daha ESKİ bir sunucu (1.4.1). Pin ederken `chroma --version` çıktısına bak.

**Neden ChromaDB?** Local, ücretsiz, Docker'a kolay eklenir, persistent storage destekler. `IS_PERSISTENT=TRUE` env var ile volume'a yazar.

**Neden hexagonal?** Kurs projesi — kurumsal mimari dersi için. Separation of concerns önemli. Yeni adapter eklemek domain'i bozmaz.

**Database URL:** `DATABASE_URL` env var yok. Ayrı `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD`, `DB_NAME` kullanılır. `src/infrastructure/config/database.py`'a bak.

**TextBlob:** Tamamen kaldırıldı. Groq ile değiştirildi. Hiçbir yerde TextBlob kullanma.

---

## MEVCUT DURUM

- **Versiyon:** v2.9 🚀 **CANLIDA: https://nexstreamnews.com** (2 Eylül 2026'da gerçek domain'e taşındı — eski `nexstreamnewsengine.duckdns.org` 13 Eyl 2026'dan beri SERTİFİKADA YOK — origin IP'yi ifşa ettiği için SAN'dan çıkarıldı, DNS kaydını duckdns.org'dan kullanıcı silecek; certbot lineage ADI hâlâ `nexstreamnewsengine.duckdns.org` (dosya yolu değişmesin diye, `certbot certificates` bunu gösterir, şaşırma). İlk canlıya çıkış: 29 Temmuz 2026. E-posta artık Resend üzerinden gidiyor (`bildirim@nexstreamnews.com`, DKIM+SPF+DMARC doğrulandı) — kişisel Gmail/SMTP artık birincil kanal DEĞİL. 2-4 Eylül'de iki ayrı deploy-kesintisi yaşandı (SSM timeout'unun host'ta zombi build süreci bırakması + nginx'in stale upstream IP'si), ikisi de kalıcı düzeltildi (detay: CHANGELOG "2 Eylül"/"3-4 Eylül"). **12 Eylül 2026 güvenlik turu (PR #126-128):** bir "güvenlik araştırmacısı" izinsiz test yapıp ücret karşılığı rapor teklif etti — A'dan Z'ye denetim yapıldı, sızıntı/zarar YOK, 6 bulgu (1 orta, 5 düşük/bilgi) aynı gün düzeltilip deploy edildi, `/security` + `security.txt` eklendi (detay: CHANGELOG "12 Eylül").
- **Test sayısı:** 931+ test, hepsi yeşil (backend); frontend `next build` temiz (React 19 + Next 16 ile, PR #93).
- **Frontend:** Next.js 16 + React 19. 10 sinematik tema (varsayılan `day`), tam TR/EN i18n, PWA (manifest + service worker). Port **3000**.
- **Mesaj kuyruğu:** Redpanda (Kafka wire-protokolü konuşan tek binary, `aiokafka` client kodu değişmedi).
- **Haber kaynağı:** 17 (TR: TRT Haber, BBC Türkçe, Hürriyet, Hürriyet Spor, Sabah, CNN Türk, Sözcü, Habertürk, HT Spor, Anadolu Ajansı, AA Ekonomi; EN: BBC Technology, BBC Sport, Guardian Tech, TechCrunch, Hacker News, The Verge).
- **CI/CD:** main'e her push → `.github/workflows/tests.yml` testleri geçirir, sonra SSM ile prod'u otomatik redeploy edip `/api/health`'i polling ile doğrular. Elle SSM SADECE manuel müdahale/debug için. Dependabot (pip+npm+github-actions, haftalık) — düzenli olarak açık PR birikir, her oturumda `gh pr list` ile göz ucuyla kontrol et.
- **Deploy akışı (24 Ağu 2026'dan beri sabit):** main'den kısa ömürlü feature branch aç → PR → merge → (otomatik) SSM'de `git checkout main && git reset --hard origin/main` → `docker compose -f docker-compose.prod.yml up --build -d` → `docker compose -f docker-compose.prod.yml restart nginx` (upstream DNS tazelemek için, 3-4 Eyl dersi). Prod artık doğrudan `main`'den deploy oluyor, ayrı bir deploy dalı YOK.
- **Hedef:** Proje ŞİMDİLİK bilinçli olarak portfolyo olarak kalıyor (24 Ağu 2026 kararı — gerçek ürüne dönüştürme AWS kredisi tükenmeden önce tekrar gözden geçirilecek). Tek VPS mimarisi bilinçli korunuyor (çoklu-bölge/HA yatırımı YOK).
- **Kısıt — bütçe GERÇEKTEN $0/ay:** AWS Free Plan'ın $100 kredisiyle karşılanıyor, günlük yakım ~$0,93 (~$28/ay) → **kredi ~Kasım 2026 ortasında tükenir**, bu tarihten önce bir karar gerekir. En iyi araştırılmış alternatif: Hetzner CX33 (~$9-10/ay); Oracle Free artık güvenilmez (limitler habersiz düşürüldü), en fazla yedek. RAM darsa ilk kapatılacaklar: Prometheus/Grafana/Loki/Promtail → Redis → backup container'ı. Detay/tam karşılaştırma: CHANGELOG.

---

## YOL HARİTASI (kalan işler)

Tamamlanan işlerin tam kronolojik dökümü `docs/CHANGELOG.md`'de. Burada sadece
GERÇEKTEN bekleyen işler var:

1. **Anasayfa tasarım yenilemesi** — kullanıcı "şu an tamamen basit bir AI
   tasarımı gibi duruyor" dedi (18 Ağu 2026), özellikle hero. Bilinçli olarak
   BAŞLANMADI — gerçek bir tasarım kararı işi, `frontend-design` skill'i ile
   ayrı/temiz bir oturumda ele alınmalı, aceleye getirilmemeli.
2. **Gerçek Stripe entegrasyonu — 24 Ağu 2026'da kullanıcı kararıyla ERTELENDİ**
   (şirket kurma/vergi levhası gibi ek hukuki-mali yük istemiyor). Kod tarafı
   hazır kalıyor ama öncelik değil. **Bunun yerine gelir yolu olarak Google
   Ads (AdSense, SADECE Free tier'da gösterilecek) değerlendiriliyor** —
   resmi kaynaklardan araştırıldı, sonuç:
   - **Şirketsiz/şahıs olarak mümkün** (Individual hesap türü yeterli).
   - **Vergi tarafında en elverişli yol GVK mükerrer 20/B istisnası**
     (325 seri no'lu Tebliğ) — vergi dairesinden/`digital.gib.gov.tr`'den
     "istisna belgesi" alıp faaliyete özel banka hesabı açmak yeterli, banka
     %15 stopaj keser, 2026 için 4. dilim tavanı (5.300.000 TL) aşılmadıkça
     bu NİHAİ vergidir — beyanname/fatura/şirket YOK. **Fiilen başvurmadan
     önce bir mali müşavirle teyit edilmeli** (araştırma resmi tebliğ
     metnine değil YMM kaynaklarının alıntılarına dayandı).
   - **Asıl darboğaz vergi değil, AdSense ONAYI:** ret nedenleri arasında
     "scraped content"/"yeterli özgün içerik yok" var, RSS-agregatör yapısı
     + neredeyse sıfır trafik riski yüksek yapıyor. **Sonuç: başvuru gerçek
     trafik gelene kadar ERTELENMELİ.** `/privacy`'yi çerez-kategorileri +
     "Ads Settings" linkiyle şimdiden hazırlamak maliyetsiz bir ön hazırlık.
     Telif riski zaten düşük (bkz. CHANGELOG "24 Ağu telif değerlendirmesi").
   - Iyzico/PayTR gibi bir alternatif hâlâ gündemde DEĞİL.
3. **Özel kaynak ekleme (custom source ingestion)** — kullanıcı kararıyla
   ŞİMDİLİK ertelendi, pricing metni "bize ulaşın" şeklinde yumuşatıldı.
   Tam private/per-user versiyonu gerçek bir mimari iş (kullanıcı bazlı veri
   izolasyonu şu an sistemde YOK).
4. **Launch içeriği** — LinkedIn metni + OG görseli hazır. Kalan: Product
   Hunt materyali, ek sosyal medya içeriği — düşük öncelik.
5. ~~Resend domain doğrulaması~~ — ✅ 2 Eylül 2026.
6. ~~Cloudflare proxy~~ — ✅ 8 Eylül 2026. Nameserver'lar Cloudflare'e taşındı
   (Full Strict SSL, Bot Fight Mode açık), `destek@nexstreamnews.com`
   Cloudflare Email Routing ile kişisel Gmail'e yönleniyor (`/contact`
   formu artık buraya gönderiyor), Google Search Console + Bing doğrulandı
   ve sitemap gönderildi. **Kritik takip düzeltmesi aynı gün yapıldı:**
   Cloudflare proxy'si nginx'in TÜM isteği kendi edge IP'sinden görmesine
   yol açıyordu (`limit_req_zone`'lar `$binary_remote_addr`'a dayanıyor —
   rate limiting "ziyaretçi başına" değil "Cloudflare node başına" işlemeye
   başlıyordu) — `set_real_ip_from`+`real_ip_header CF-Connecting-IP` ile
   düzeltildi (bkz. BİLİNEN NOTLAR).
7. **Dependabot PR'ları** — düzenli triyaj gerekiyor (`gh pr list` ile
   kontrol et). **8 Eylül 2026 durumu:** React 19 +
   Next 16 zaten merge (PR #93). Tailwind 3→4 ve TypeScript 5→7 hâlâ build
   kırık halde bekliyor (v4/v7 migration adımları gerekiyor), ~14 npm/pip
   patch-minor PR hiç triyaj edilmedi. Review/merge kararı kullanıcıda.
8. ~~Hesap silme endpoint'i~~ — ✅ 19 Ağu 2026.
9. ~~Analytics/hata takibi~~ — ✅ 25 Ağu 2026 (Sentry + PostHog).
   ~~İletişim/telif kanalı~~ — ✅ 8 Eylül 2026, `POST /contact` +
   `/contact` sayfası (Resend ile `CONTACT_RECIPIENT_EMAIL`'e iletiliyor,
   kişisel e-posta public'te sergilenmiyor).
10. ~~Rakip taraması sonrası quick-win paketi~~ — ✅ 19 Ağu 2026.
11. ~~Story cluster görünümü~~ — ✅ 19 Ağu 2026.
12. ~~Web Push bildirimleri~~ — ✅ 25 Ağu 2026.
13. ~~RAG tabanlı "bu konuda soru sor" mini sohbet~~ — ✅ 26 Ağu 2026 canlıya
    çıktı. **Bilinçli olarak henüz çözülmeyen bir bulgu:** retrieval bazen
    doğru haberi buluyor ama kanıt paketi "maç" gibi genel bir kelimeyi
    paylaşan ama tamamen alakasız haberlerle doluyor — sorguda geçen özel
    ismin (ör. takım adı) kanıt paketindeki HER makalede literal doğrulanmasını
    gerektiren ayrı bir tasarım turu ister (bounded bir yama değil). Detay:
    CHANGELOG "LLM modülü bölme spike'ı" ve RAG bug turu notları. Ayrıca
    spec'in tam 5 senaryolu QA turu VE tarayıcıda oturum ayrımı/free-tier
    kilit ekranı kontrolü hâlâ tam yapılmadı.
14. **Özet (summary) clickbait başlığı papağan gibi tekrarlamamalı** (19 Ağu
    2026, kullanıcı örnek verdi). Groq prompt'u (`adapters/analysis/
    common.py`) özetin başlıktaki belirsizliği ÇÖZMESİNİ, içerikten somut
    isim/varlık çıkarmasını isteyecek şekilde güçlendirilmeli. Bounded bir
    prompt-engineering işi, kendi test turu ister.
15. ~~Admin panelinde /admin/users tablosu sıralanabilir~~ — ✅ 26 Ağu 2026.
16. ~~Test paketi sağlık denetimi~~ — ✅ 25 Ağu 2026 (sonuç: sağlıklı).
17. ~~Kullanıcı banlama (moderatör/admin)~~ — ✅ 19 Ağu 2026.
18. **Gerçek makale metni scraping (okuma süresi için)** — okuma süresi
    rozeti 20 Ağu 2026'da kaldırıldı (DB'deki `content` sadece RSS teaser'ı,
    ~30-80 kelime, gerçek makale hiç çekilmiyor). 17 kaynağın makale
    sayfasından tam metin çekmek (Readability/BeautifulSoup tarzı,
    HTML yapısı kaynak başına farklı → kırılgan) ayrı bir roadmap maddesi;
    ingest-anında mı on-demand mı çekileceği de ayrı bir karar.
19. ~~Arama ilişkisel sorgu genişletme~~ — ✅ 20 Ağu 2026.
20. ~~Deploy pipeline'ı main merge'ine bağla~~ — ✅ 24-25 Ağu 2026.
21. ~~"Kaynaklar" (story cluster) UI'ının kullanışlılığı~~ — ✅ 24 Ağu 2026.
22. ~~Entity chip → arama~~ — ✅ 24 Ağu 2026 (PR #51).
23. ~~Stratejik "buzdağı" değerlendirmesi~~ — ✅ 24 Ağu 2026 (bkz. MEVCUT
    DURUM "Hedef" satırı).
24. ~~LLM modüllerini bölme fizibilitesi~~ — ✅ 27 Ağu 2026 (Groq TPD kotası
    MODEL BAŞINA ayrı havuz; `GroqQuestionAnswerer` + `GroqQueryExpander`
    ikisi de `gpt-oss-120b`'ye taşındı, worker'ın haber analiz hattı 20b
    havuzunun TEK tüketicisi).
25. **Groq günlük token/hacim maliyetini düşürme — 1. dilim (prompt
    sıkıştırma) ✅ + 2. dilim (burst-pacing kök neden düzeltmesi, PR #85,
    1 Eyl) ✅.** Kök neden canlı header probe'larıyla bulundu: Groq'un
    limiti günlük kota değil sürekli dolan bir "leaky bucket" — toplam
    tüketim rahat olsa bile BURST halinde istek atmak kovayı anlık boşaltıp
    dakikalarca 429'a yol açıyor. `groq_request_interval_seconds` (4.0s)
    üç noktada (makale-arası, `reanalyze_missed`, kaynaklar-arası) tek
    doğruluk kaynağı yapıldı. **Sonraki oturumun işi: birkaç günlük
    gözlemle (worker log'unda `rate limit` sıklığı) gerçekten işe yarayıp
    yaramadığını doğrulamak** — yaramazsa tamamlayıcı kol hâlâ aynı:
    `is_near_duplicate` kontrolü Groq analizinden SONRA çalışıyor, near-
    duplicate haberler bile tam analiz alıyor (ürün kararı gerektiriyor,
    bounded değil).
26. **`/contact` formundan gönderilen mailler spam'e düşüyor (8 Eylül 2026,
    kullanıcı bulgusu, henüz çözülmedi)** — SPF şüphelendirdi ama ÇIKMAZ
    sonucu: Resend zaten `send.nexstreamnews.com` alt-domain'i üzerinden
    kendi doğrulamasını yapıyor (2 Eylül'den beri kurulu `rsend`/`send`
    CNAME'leri), root SPF'e Resend'i eklemeye GEREK YOK. **Sonraki
    oturumun ilk işi:** kullanıcı spam'e düşen bir maili Gmail'de "Orijinali
    göster" ile açıp `Authentication-Results` satırını (SPF/DKIM/DMARC
    pass/fail) paylaşacak — kesin teşhis oradan. En muhtemel açıklama
    domain'in gönderim geçmişinin çok yeni olması (6 gün) + o anki test
    mesajlarının bot gibi okunan içeriği, ikisi de zamanla/gerçek kullanıcı
    trafiğiyle kendiliğinden düzelebilir. **Spam teşhisi hâlâ AÇIK** —
    yukarıdaki "Sonraki oturumun ilk işi" hâlâ geçerli.
    ~~Bağımsız iyileştirme~~ — ✅ 11 Eylül 2026: mesajlar artık mail ile
    birlikte admin panelden de görülebiliyor (`POST /contact` `contact_
    messages` tablosuna da yazıyor, `/admin/contact-messages` sayfası
    `/admin/sponsors` deseniyle listeliyor+okundu işaretliyor) — TDD ile
    yazıldı, e-posta başarısız/yapılandırılmamış olsa bile mesaj kaybolmuyor.

27. **Kaynak sağlığı taraması — 10 Eylül 2026, kullanıcı isteğiyle başlatıldı.**
    Prod API'den (`GET /api/v1/news?source=...`) 17 kaynağın hepsinin en son
    haber tarihi tek tek kontrol edildi:
    - ~~**Anadolu Ajansı + AA Ekonomi 9 gündür (1 Eylül'den beri) hayalete
      düşmüştü**~~ — ✅ **10 Eylül 2026'da düzeltildi (PR #110).** Kök neden:
      `BaseRssScraper` tüm kaynaklara sabit `User-Agent: Mozilla/5.0`
      gönderiyordu — gerçek tarayıcıların asla tek başına göndermediği
      klasik bot imzası. AA'nın WAF'ı bunu TLS seviyesinde reddediyordu
      (canlı curl testiyle doğrulandı: bare UA 3/3 red, gerçekçi tam Chrome
      UA'sı 3/3 başarı — hem local'den hem prod EC2 IP'sinden). Fix tüm 17
      kaynağın paylaştığı tek noktadan (`BaseRssScraper._USER_AGENT`) yapıldı,
      TDD ile (`test_fetch_content_sends_realistic_browser_user_agent`),
      deploy sonrası prod'dan canlı doğrulandı.
    - **🟡 Guardian Tech, TechCrunch, Hacker News, The Verge — muhtemel kök
      neden bulundu (henüz TAM doğrulanmadı, bkz. yukarıdaki madde 25).**
      8 Eylül
      ~14:30-15:15 UTC civarında (registry'de art arda son 4 kaynak)
      neredeyse aynı anda durdular. Worker container'ı o tarihten beri
      sağlıklı (RestartCount=0 — çökmüş/takılı kalmış DEĞİL) ve 4 feed de
      hem local'den hem prod EC2 IP'sinden gerçekçi UA ile 200 dönüp GÜNCEL
      içerik veriyor — kaynak tarafında kırılma yok. **10 Eylül'deki deploy
      sonrası worker log'u canlı izlenirken yakalandı:** startup-scrape
      SADECE registry'nin 1. kaynağını (TRT Haber, 3 yeni haber) bitirmek
      için **7.5 dakika** sürdü — Groq rate limit'e art arda takılıp tek bir
      beklemede 184 saniye harcadı (`groq_analyzer: "Groq rate limit, 184s
      bekleniyor..."`). Roadmap #25'teki burst-pacing düzeltmesi (1 Eylül)
      GÖRÜNÜŞE GÖRE yetersiz kalmış — sıralı işleyen worker bu hızda
      registry'nin 14-17. sıralarındaki (Guardian Tech→Verge) kaynaklara
      makul bir sürede hiç ulaşamayabilir, 10dk'lık scheduler aralığı da bu
      arada yeni run'lar tetikleyip kuyruğu büyütüyor olabilir. **Sonraki
      oturumun işi:** birkaç saatlik worker log gözlemiyle (`docker logs
      nexstream_worker | grep "Güncelleme başladı"`) worker'ın bu 4
      kaynağa GERÇEKTEN ulaşıp ulaşmadığını doğrulamak; ulaşıyorsa kök
      neden başka yerde, ulaşamıyorsa bu roadmap #25'in daha ciddi bir
      versiyonu ve `worker_max_new_articles_per_run`/kaynak başına zaman
      bütçesi gibi bir çözüm gerektiriyor (ürün kararı, bounded değil).
    - ~~**Guardian Tech/TechCrunch/HN/Verge + AA/AA Ekonomi asıl kök nedeni
      bulundu ve düzeltildi (PR #114, 10 Eylül 2026).**~~ Yukarıdaki Groq-
      throttling teorisi YANLIŞ/ikincildi — asıl neden `docker-compose.
      prod.yml`'deki `SCRAPE_SOURCES`'ın bu 6 kaynağı hiç içermemesiydi,
      scheduler onları hiç tetiklemiyordu. Fix + regresyon testi
      (`tests/infrastructure/test_deployment_config.py`, prod/dev compose
      `settings.py` varsayılanıyla senkron kalmasını garanti eder) deploy
      edildi, scheduler log'unda 17/17 kaynağın gönderildiği SSM ile
      doğrulandı. Bu tür bir servis eklenip sadece dev compose'a/
      settings.py'a yazılıp prod compose'un unutulması riskini genelleştir.
    - **Yeni konu için araştırılan kaynak adayları (henüz registry'ye
      EKLENMEDİ, kullanıcı onayı bekliyor):** hepsi canlı curl ile doğrulandı
      (200 + güncel `pubDate`).
      - *Ekonomi/finans/kripto:* Dünya Gazetesi (`dunya.com/rss`, TR),
        Cointelegraph (`cointelegraph.com/rss`), CoinDesk
        (`coindesk.com/arc/outboundfeeds/rss/`, 308 redirect var ama
        `follow_redirects=True` zaten hallediyor). **Bloomberg HT
        (`bloomberght.com/rss`) ELENDİ** — feed 200 dönüyor ama kendi
        `lastBuildDate`'i 16 gündür güncellenmemiş, kaynağın kendisi zaten
        hayalete düşmüş.
      - *Bilim/sağlık:* ScienceDaily (`sciencedaily.com/rss/all.xml`, EN),
        NASA News Release — **URL değişti**, eski
        `nasa.gov/rss/dyn/breaking_news.rss` 301 ile
        `nasa.gov/news-release/feed/`'e yönleniyor, yeni URL doğrudan
        kullanılmalı.
      - *Dünya/uluslararası:* Al Jazeera English
        (`aljazeera.com/xml/rss/all.xml`), DW English
        (`rss.dw.com/xml/rss-en-all`). NPR World
        (`feeds.npr.org/1004/rss.xml`) canlı ama içerik bazen "evergreen"
        (güncel olmayan) makaleler karıştırıyor, dikkatli seçilmeli. Reuters
        World resmi RSS'i kapatılmış (404) — ELENDİ.
      - Hepsi mevcut `BaseRssScraper`'a (RSS+Atom otomatik, redirect otomatik)
        sıfır ek kod ile uyuyor — iş sadece alt sınıf + registry satırı.
    - **Reddit — beklenenden daha fazla fizibıl çıktı.** `reddit.com/r/<sub>/
      .rss` endpoint'i hem local'den hem **prod EC2 IP'sinden** (SSM ile
      doğrulandı) gerçekçi UA ile 200 dönüyor (bare UA ile 403 — aynı UA
      sınıfı sorunu). Datacenter-IP engeli TEYİT EDİLMEDİ (aksine, prod IP'si
      sorunsuz erişebiliyor) — daha önce "muhtemelen engellenir" varsayımı
      YANLIŞ çıktı, gerçek IP testi yapmadan varsayma. Mimari zaten uyumlu
      (Atom formatı destekleniyor). Kullanıcı onayı olursa bir sonraki adım:
      deneme amaçlı 1-2 subreddit ekleyip deploy sonrası gerçek ingest'i
      worker log'undan doğrulamak.
    - **Twitter/X:** kasıtlı kapsam dışı kararı DEĞİŞMEDİ (bkz. aşağıdaki
      liste) — bu tur kararı yeniden değerlendirmedi.
28. **Deploy build'ini EC2 dışına (GitHub Actions runner'ına) taşımak —
    11 Eylül 2026'da t3.small'ı üç kez tamamen tıkayan (SSM Agent bile
    yanıt veremedi, 3 reboot gerekti) prod kesintisinin GERÇEK kalıcı
    çözümü.** Kök neden `docker compose up --build -d`'nin EC2 üzerinde
    hem build hem 16 container'ın recreate'ini aynı anda yapması — anlık
    RAM/CPU darboğazı yaratıyor (embedder gibi RAM-ağır bir servisin ESKİ
    ve YENİ kopyası kısa süre aynı anda bellekte kalabiliyor). Image'ı
    GitHub Actions runner'ında build edip ücretsiz bir registry'ye (GHCR)
    push etmek, EC2'nin sadece `docker pull`+`up -d` yapmasını sağlar —
    build hiç EC2'de olmaz. **Ara-önlem (PR #124, aynı gün) uygulandı ve
    YETERLİ göründü:** build+health-check penceresinde RAM-ağır izleme
    servisleri (Prometheus/Grafana/Loki/Promtail) geçici durduruluyor,
    sonraki deploy sorunsuz tamamlandı. **Kullanıcı CPU Credit "Unlimited"
    moduna geçmeyi bilinçli REDDETTİ** (küçük de olsa bir maliyet riski
    istemedi) — bu yüzden registry'ye taşıma tek gerçek "$0 garantili"
    kalıcı çözüm. Bounded değil, ayrı bir tasarım/plan turu gerektirir
    (registry auth, image tagging/versioning, workflow yeniden yazımı).
    Tekrar bir tıkanma yaşanırsa ÖNCELİK bu maddeye verilmeli. Detay:
    CHANGELOG "11 Eylül prod kesintisi".

29. **Güvenlik turu (12 Eyl 2026) — KULLANICININ AWS KONSOLUNDAN yapması
    gereken 2 iş (deploy IAM kullanıcısının Security Group yetkisi YOK, kod
    tarafından yapılamaz):**
    - **SSH 22 portunu dünyaya kapat** — sunucuya SSM ile bağlanıyoruz, 22'ye
      hiç ihtiyaç yok; 3 günde 757 başarısız SSH denemesi görüldü (arka plan
      gürültüsü ama gereksiz yüzey). EC2 → Security Groups →
      `sg-061424eb4ff9eb775` → Inbound → 22 kuralını sil.
    - **80/443'ü SADECE Cloudflare IP aralıklarına aç** (`cloudflare.com/ips-v4`
      + `ips-v6`, nginx.conf'taki `set_real_ip_from` listesiyle aynı) —
      origin IP'si (63.178.59.10) doğrudan cevap veriyor, Cloudflare'in Bot
      Fight Mode/WAF'ı atlanabiliyor ve loglarda IP'ye doğrudan tarama var.
      **Ön şartlar 13 Eyl 2026'da TAMAMLANDI:** duckdns SAN'ı sertifikadan
      çıkarıldı (yeni cert sadece nexstreamnews.com + www, Aralık 2026'ya kadar),
      nginx 443 bloğuna ACME webroot location'ı eklendi (CF 'Always Use HTTPS'
      yenilemeyi kırmasın). **Kalan:** (a) kullanıcı duckdns.org'dan subdomain'i
      siler, (b) SG'de 80/443 kaynağı CF aralıklarıyla değiştirilir — bunu
      Claude'un yapabilmesi için `nexstream-deploy` IAM kullanıcısına
      `ec2:DescribeSecurityGroups` (Resource *) + `ec2:AuthorizeSecurityGroupIngress`/
      `ec2:RevokeSecurityGroupIngress` (sadece sg-061424eb4ff9eb775) eklenmeli.
    - **GitHub → Settings → Emails:** "Keep my email addresses private" ve
      "Block command line pushes that expose my email" işaretle (adresin
      commit'lerden sızmasını keser; geçmiş için bkz. BİLİNEN NOTLAR).
    - Ayrıca 3. parti hesaplar (AWS root + IAM, Cloudflare, GitHub, domain
      kayıt firması, Resend, Groq, Gmail) için MFA/2FA + parola yöneticisi
      kontrol listesi kullanıcıya iletildi — kod tarafında karşılığı yok.

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

**⚠️ `npm run build`'i frontend container ÇALIŞIRKEN host'ta ÇALIŞTIRMA:** `docker-compose.yml` frontend'i `.:/app` volume ile mount ediyor ve container içinde `npm run dev` koşuyor. Host'ta `npm run build` çalıştırmak paylaşılan `.next` klasörünü PROD çıktısıyla eziyor → dev server'ın beklediği chunk dosyaları kaybolur, sayfa HTML 200 döner ama TÜM CSS/JS 404 verir. **Kurtarma:** `docker compose stop frontend` → `rm -rf frontend/.next` → `docker compose start frontend` → tarayıcıda Ctrl+Shift+R. Tip kontrolü gerekiyorsa ya önce container'ı durdur ya da `npx tsc --noEmit` kullan (`.next`'e dokunmaz). Container çalışmıyorsa host'ta build sorunsuz, ama sonrasında `rm -rf frontend/.next` ile prod build kalıntısını temizle (bir sonraki `docker compose up frontend` dev server'ıyla çakışmasın).

**Docker build — pip hash hatası ve uzun build süresi:** `Dockerfile`/`Dockerfile.light`'ta `RUN --mount=type=cache,target=/root/.cache/pip pip install --retries 10 --timeout 120 -r requirements.txt` kullanılıyor (BuildKit cache mount + retry). `--no-cache-dir` ya da tam temiz build denemek `THESE PACKAGES DO NOT MATCH THE HASHES` hatasını (indirme bozulması, hash sorunu DEĞİL) BÜYÜTÜR — her seferinde farklı pakette patlar. Wheel'ler image katmanına girmez ama build'ler arasında saklanır.

**Telefondan/başka cihazdan (aynı hotspot/LAN) erişim:** `.env`'e geçici `NEXT_PUBLIC_API_URL=http://<LAN-IP>:8000` + `CORS_ORIGINS`'e `<LAN-IP>:3000` eklenip `docker compose up -d app frontend` ile uygulanır (Windows "Public" ağ profili gelen bağlantıları engeller — admin PowerShell'de `New-NetFirewallRule` gerekir). **İş bitince mutlaka geri al** — Public profildeki kalıcı bir güvenlik açığı.

---

## BİLİNEN NOTLAR

Her madde tek bir kalıcı kural — "ne zaman/nasıl bulundu" forensic detayı
`docs/CHANGELOG.md`'de (tarihe göre aranabilir).

- **SSM/CI'ın "Failed"/timeout raporlaması, host'taki alttaki process'in de
  öldüğü anlamına GELMEZ** (özellikle `docker buildx`/BuildKit gibi arka
  planda devam eden async işlerde) — kesilen bir `docker compose up --build`
  host'ta zombi süreç bırakıp kaynak tüketip 504'e yol açabilir. Kaynak
  kısıtlı bir makinede build ARG'ı değiştiren bir deploy'dan sonra
  `uptime`/`free -h` ile MUTLAKA doğrula, sadece CI'ın yeşil/kırmızısına
  güvenme. Kurtarma bounded bir "kill PID" değil `aws ec2 reboot-instances`.
- **`git checkout main` sonrası (PR merge/deploy izleme bitince) yeni bir
  istek gelirse, kod değişikliğine başlamadan ÖNCE `git branch
  --show-current`'ı reflekse çevir** — "main'deyim" hissi ile "main'e commit
  atmak güvenli" hissi karışabiliyor, birden fazla kez yaşandı.
- **Bir worker/consumer N işi SIRAYLA ve HER BİRİNİ TAMAMEN bitirerek
  işliyorsa, biri yavaşlarsa (rate limit/ağ) diğerleri süresiz aç
  kalabilir** — yeni böyle bir desen eklerken kalem başına üst sınır düşün
  (bkz. `worker_max_new_articles_per_run`, `NewsService.
  update_news_from_source(..., max_new_articles=...)`).
- **Groq'un TPM ve TPD limitleri BAĞIMSIZ havuzlar** — biri için proaktif
  throttle eklemek diğerini çözmez; hangi limitin gerçekten bağlayıcı
  olduğunu ölçmeden varsayma. Ayrıca Groq'un rate limit'i "günlük kota" gibi
  görünse de aslında sürekli dolan bir **leaky bucket** (kanıt: `x-
  ratelimit-reset-requests` istek başına tam 86.4s artıyor) — toplam
  tüketim rahat olsa bile BURST halinde istek atmak kovayı boşaltıp
  dakikalarca 429'a yol açar. Tek doğruluk kaynağı: `groq_request_
  interval_seconds`.
- **TPD/token maliyeti tahminini SSM/log analizine hiç dokunmadan (statik
  prompt-uzunluğu hesabıyla) canlı ölçümle çapraz doğrulamak mümkün** —
  hangi lever'ın gerçek kazanç vereceğine dair güvenilir bir ön cevap verir.
  Bir kırpma/limit lever'ının etkisi olup olmadığını, o alanın GERÇEKTE ne
  kadar dolu olduğuna bakmadan varsayma (`text[:1000]` örneği: RSS teaser'ı
  zaten 30-80 kelime, kırpma sınırının çok altında).
- **Yeni bir router/endpoint'te 3. parti bir entegrasyonu (email/Sentry/
  PostHog gibi) tek bir DI noktasında (`get_email_adapter` gibi) mock'lamak
  kırılgan** — bir sonraki endpoint aynı hatayı tekrarlayabilir. Ağ
  SINIRININ kendisini (`smtplib.SMTP`, `requests.post`, `sentry_sdk.init`)
  autouse bir fixture'la kapatmak (bkz. `tests/conftest.py`) daha sağlam.
- **Türkçe "yanlış dost" kök çakışması** (örn. "altın" kökü "alt+ında/ki"
  çekimleriyle harf düzeyinde çakışıyor, `\b`-anchor tek başına yetmiyor) —
  kök→bilinen-çakışan-TAM-KELİME sözlüğü gerekiyor (bkz.
  `subscriber_matching.py::_FALSE_FRIEND_WORDS`). Yeni bir keyword-eşleştirme
  şikayeti gelirse bu sınıfı kontrol et — arama tarafı (`news_service.
  _stem_tr`) AYNI riski taşıyor ama henüz düzeltilmedi.
- **`frontend/lib/api.ts`'teki TÜM `/api/v1/*` çağrıları (`${BASE}/api/v1/
  ...`) nginx'in dedicated `/api/v1/` bloğunu HİÇ kullanmıyor, şans eseri
  çalışıyor** (prod'da `NEXT_PUBLIC_API_URL=/api`, gerçekte istek `/api/api/
  v1/...`'e gidip nginx'in genel `/api/` bloğuna düşüyor, tesadüfen doğru
  yere iniyor). Henüz düzeltilmedi — ya `api.ts`'teki v1 çağrılarını
  `${BASE}/v1/...`'e çevir ya da nginx `/api/v1/` bloğunu güncelle.
- **Site 8 Eyl 2026'dan beri Cloudflare proxy'sinin arkasında** — nginx `set_real_ip_from`+`real_ip_header CF-Connecting-IP` ile Cloudflare'in edge IP'lerini güvenilir sayıp gerçek ziyaretçi IP'sini okuyor (bkz. `infra/nginx/nginx.conf`). Bu YOKSA `$remote_addr` TÜM ziyaretçiler için Cloudflare'in birkaç edge IP'sine düşer — `limit_req_zone`'lar (rate limiting) ve app'e giden `X-Real-IP` (slowapi'nin dayandığı) "ziyaretçi başına" değil "Cloudflare node başına" işlemeye başlar. Cloudflare'in IP aralığı nadiren değişir ama değişirse `nginx.conf`'taki liste `cloudflare.com/ips-v4`+`ips-v6`'dan güncellenmeli.
- **CI/CD'nin kendi sağlık kontrolü, Cloudflare/WAF arkasındaki public domain'e DIŞARIDAN atılmaz** — genel amaçlı CI runner'ları (GitHub Actions, datacenter IP) Cloudflare'in Managed Challenge'ını (`cf-mitigated: challenge`, User-Agent'tan bağımsız, saf IP-reputation bazlı) tetikleyip hep 403 alır; bu User-Agent değiştirerek ÇÖZÜLEMEZ (AA scraper fix'inden farklı sınıf bir sorun). Health-check aynı SSM/SSH oturumunda sunucunun KENDİ `localhost`'undan yapılmalı (bkz. `infra/scripts/wait_for_health.sh`). Detay: CHANGELOG "PR #110-120".
- Groq free tier: 14.400 req/gün — production'da dikkat
- Scraper limit: 25 haber/kaynak/çalışma
- DB duplicate kontrolü var — aynı URL tekrar kaydedilmez
- ChromaDB 1.5.5 kurulu (0.5.23 uvicorn conflict veriyordu)
- `docker-compose down -v` sonrası ChromaDB da sıfırlanır
- Dashboard sidebar kaldırıldı, tüm kontroller üst bar'da
- `prometheus-fastapi-instrumentator` app'e eklendi, `/metrics` endpoint Prometheus format döndürür
- `docker-compose.prod.yml` production için, `docker-compose.yml` dev için kullanılır
- `infra/nginx/nginx.dev.conf` SSL olmadan local test için (nginx.conf SSL gerektirir)
- Worker sıralı işleme: `asyncio.create_task` → `await` + throttle, Groq rate limit patlamasını önler
- Ölü besleme worker'ı çökertmez (scraper exception'ı yutar, [] döner)
- **v1.8 cloud fallback:** `HUGGINGFACE_API_KEY` boşsa fallback devre dışı. Analyzer `factory.build_analyzer()` ile kurulur, `GroqAnalyzer()` doğrudan çağrılmaz. `FallbackAnalyzer.analyze_text` asla fırlatmaz (nötr fallback)
- **v1.8 related:** ilişki grafı ayrı tablo değil, on-the-fly entity overlap (son 500 entity'li haber taranır)
- **v1.8 skorlama:** `quality_score`+`credibility_score`+`corroboration_count` ingest'te `service._enrich_metadata` ile set edilir; saf hesap `domain/scoring/`'de
- **v1.8/v1.9 migration'lar:** `migrations/v1_8_quality_credibility.sql`, `migrations/v1_9_users_sessions_usage_sponsor.sql` — dev'de `create_all` otomatik ekler, prod'da elle çalıştırılmalı
- **v1.9 auth (v1.12'de cookie'ye taşındı):** kimlik birincil olarak HttpOnly `nxs_session` cookie'si; `X-Session-Token` header sadece SSR/test fallback'i. bcrypt direkt kullanılıyor (passlib yerine — 5.x uyumsuzluğu)
- **Dev'de session cookie gotcha:** `session_cookie_secure` varsayılanı `True` — `SESSION_COOKIE_SECURE=false` eklenmezse cookie local HTTP dev'de tarayıcıya hiç gitmez. Dev compose'a zaten eklendi, yeni bir varyant açarsan unutma.
- **v1.9 tier:** `check_tier_limit` dependency v1 router'da, Free=100/gün, Pro=2000/gün, Enterprise=sınırsız
- **v1.9 billing:** Stripe yapılandırılmazsa `/billing/*` → 503. Webhook `stripe-signature` doğrulaması yapılır
- **Tailwind responsive class + inline style çakışması:** `hidden md:flex` gibi responsive display class'ı olan bir elemente inline style'a ASLA `display` ekleme — inline style class'ı ezer, `md:hidden` çalışmamış gibi görünür. Açık/kapalı mobil panellerde ayrıca `matchMedia("(min-width: 768px)")` ile ekran büyüyünce state'i otomatik kapatan bir effect ekle.
- **v1.10 tema/i18n:** Renk token'ları `globals.css`'te `[data-theme="<id>"]`, TÜM string `lib/i18n.ts`'te (`UI[lang]`) — sayfaya hardcoded metin YAZMA. Trending API alanı `name` (eskiden `entity` bekleniyordu, boş isim bug'ıydı).
- **v1.10 kafka dayanıklılığı:** kafka/zookeeper/chromadb'ye `restart: unless-stopped`. `KafkaPublisherAdapter.start()` retry'lı. Temiz aç/kapa: `docker compose down` → `up -d`.
- **v1.10 node lokal:** Node v24 host'ta. Docker `Dockerfile.dev` `npm run dev` (SWC) tam tip kontrolü YAPMAZ — tip hataları sadece `next build`'te görünür.
- **v1.11 admin yetkisi:** `require_admin`/`require_moderator` X-API-Key VEYA rol tabanlı kullanıcı oturumu kabul eder. **`get_current_user` (zorunlu) X-API-Key'i ASLA çözmez** — yeni bir admin-yazma endpoint'i eklerken handler'da `actor: Optional[User] = Depends(get_optional_user)` deseni kullan (`get_current_user` değil), yoksa router X-API-Key'i kabul etse bile handler 401 verir.
- **v1.11 kullanıcı API key:** `nxs_` önekli, `/account/api-key` ile yönetilir, `X-User-Key` header'ı ile. Session ile aynı anda gelirse session kazanır.
- **slowapi + çoklu worker gotcha'sı:** prod `--workers 2` — `storage_uri` (Redis) set edilmezse her worker kendi in-memory sayacını tutar, limit fiilen ~2 katına gevşer. `REDIS_URL` prod'dan kaldırılırsa rate limit SESSİZCE gevşer, hata vermez.
- **Prod deploy öncesi kontrol listesi:** `FRONTEND_URL`, `RESEND_API_KEY`/`EMAIL_FROM`, `ENVIRONMENT=production`, `API_KEY` (rastgele), `CORS_ORIGINS` (gerçek domain, `*` DEĞİL), `GRAFANA_PASSWORD` (compose `:?` ile zorunlu), `SESSION_COOKIE_SECURE=true` — ilk dördü zayıf/eksikse `_reject_unsafe_production_config` uygulamayı açılışta ÖLDÜRÜR (kasıtlı).
- **`ENVIRONMENT=production` guard'ı "hepsi ya da hiçbiri" uygulanır** — worker/scheduler gibi HTTP'siz bir servise bu env var'ı eklersen, guard'ın kontrol ettiği `API_KEY`/`CORS_ORIGINS`/`SESSION_COOKIE_SECURE`/`BILLING_DEV_MODE`'un HEPSİNİ o serviste de gerçek değerleriyle geçirmen gerekir (servisin bunları kullanıp kullanmaması ÖNEMLİ DEĞİL, guard'a görünür olmaları yeterli) — yoksa `Settings()` import anında patlar, container crash-loop'a girer. Deploy sonrası `docker inspect --format '{{.State.Status}}'`/`RestartCount` ile doğrula, sadece `/api/health`'e bakma (app sağlıklı görünürken worker sessizce çökebiliyor).
- **Yerel `.env`'e gerçek bir 3. parti anahtarı (Sentry DSN vb.) eklemeden önce test suite'in onu GERÇEKTEN mock'ladığından emin ol** — "zaten hep boştu, hiç test edilmedi" bir varsayım, garanti değil (bkz. `tests/conftest.py`'deki autouse fixture'lar).
- **Yeni bir `DELETE`/`PATCH` endpoint'i body'den bir ID/endpoint/anahtar alıp bir kaynağı hedefliyorsa, o kaynağın `current_user`'a ait olduğunu SORGULAYARAK doğrula** (IDOR varsayılan risk) — sadece "girdi doğru formatta mı" yeterli değil.
- **Senkron/kullanıcı-yüzlü bir HTTP isteğinde çalışan bir LLM adapter'ı, arka plan worker'ının 429/Retry-After bekleme desenini (dakikalarca `time.sleep`) KOPYALAMAMALI** — interaktif yolda 429'da fail-fast (hemen hata döndür), worker/background'da sabırla bekle. Var olan bir adapter'ı kopyalarken çağrıldığı bağlamı da sorgula.
- **Groq'un günlük (TPD) token kotası MODEL BAŞINA ayrı bir havuz** — paylaşılan tek bir sayaç DEĞİL. Yeni bir LLM-tüketen özellik eklerken worker'ın modeliyle (`gpt-oss-20b`) AYNI modeli paylaşıp paylaşmadığını kontrol et, paylaşıyorsa aynı tıkanıklığı miras alır (RAG/query-expansion bu yüzden `gpt-oss-120b`'ye taşındı).
- **nginx container'ında log dosyaları gerçek dosya değil `/dev/stdout`/`/dev/stderr` symlink'i** — `docker exec nginx wc -l ...` SONSUZA kadar asılı kalır. Doğru yol: `docker logs <container>`.
- **Playwright'ın Chromium indirmesi bu ortamda güvenilmez/çok yavaş** (~200KB/s, sık sık timeout) — "exit code 0" indirmenin bittiği anlamına gelmez. Zaman kısıtlıysa canlı tarayıcı doğrulamasından vazgeç, kod incelemesi + build/curl smoke-test'e güven, kullanıcıya açıkça söyle.
- **Bash `git commit -m` mesajında backtick KULLANMA** — shell komut ikamesi sanıp çalıştırır, mesajdan o parça sessizce silinir. Tek tırnak kullan.
- **Dependabot birbirine bağımlı (peer dependency) paketleri bazen YANLIŞ ayrı PR'lara böler** — bir bump PR'ı "peer dependency" hatasıyla kırıksa, yakın bir kardeş paket için ayrı bir PR olup olmadığını kontrol et, elle birleştirmek gerekebilir.
- **Bir Dependabot "majör bump" PR'ının gerçek riskini değerlendirmeden önce `requirements.txt`'te o paketin PİNLİ mi (`==`) yoksa ARALIKLI mı (`>=`) olduğuna bak** — aralıklıysa (`bcrypt>=4.0.0`, `redis>=5.0.0` gibi) her fresh install zaten en son sürümü çekiyordur, PR sadece dokümante edilen alt sınırı gerçeğe eşitler, FONKSİYONEL DEĞİŞİKLİK YOKTUR (10 Eylül 2026'da redis 5→8/bcrypt 4→5 böyle çıktı). Gerçek riski taşıyan sadece pinli paketlerdir (`sentence-transformers==3.3.1` gibi) — onlar için mock'lu CI'a güvenme, gerçek kod yoluyla (örn. gerçek model/gerçek hash) doğrula.
- **Çok sayıda bağımsız Dependabot PR'ını tek deploy'da birleştirirken** her dalı `git merge origin/<dal>` ile ayrı ayrı uygula (aynı satırı değiştiren ardışık bump'larda küçük conflict'ler çıkar, elle çöz) — frontend `package-lock.json` için ise dalları merge ETME, hedef versiyonları `npm install <pkg>@<version>` ile TEK SEFERDE kur (çok-yönlü lockfile merge conflict'inden kaçınır).
- **Roadmap maddesini "sıradaki oturumun İLK işi" diye not düşüp session'ı bitirmek, o işin GERÇEKTEN yapıldığını garanti etmez** — aynı gün başka bir dalda yapılmış olabilir. Başlamadan önce `git log --oneline -S"<anahtar kelime>"` ile doğrula.
- **AWS SSM operasyon deseni:** komutlarda `git` kullanmadan önce `export HOME=/home/ubuntu` + `git -c safe.directory=<repo-path>` (repo: `~/NexStream-News-Engine`) gerekir. Windows'taki native `aws.exe`'ye Git Bash'ten `file:///...` paramfile yolu VERME — JSON'u inline geç. Çıktıda Türkçe karakter varsa (`get-command-invocation` sonucu) `aws.exe` Windows'ta `'charmap' codec can't encode` ile patlar — `chcp.com 65001` + `export PYTHONIOENCODING=utf-8:replace` ile çöz.
- **`docker compose up --build -d` sırasında (özellikle birden fazla image aynı anda rebuild olunca) t3.small'in 1.9GB RAM'i yetersiz kalabiliyor** — `nexstream_embedder` (ML modelini RAM'de tutan servis) ilk kurban oluyor (`OOMKilled=true`, 10 Eylül 2026'da canlıda gözlemlendi). `restart: always` sayesinde birkaç dakikada kendi kendine toparlanıyor ama deploy sonrası SADECE `Up`/`healthy` durumuna değil `docker inspect <container> --format '{{.State.OOMKilled}}'`e de bak.
- **11 Eylül 2026 — bu OOM riski BÜYÜYÜP ÜÇ KEZ instance'ı TAMAMEN tıkadı** (SSM Agent bile "Undeliverable"/"Delayed" döndü, sadece embedder değil TÜM sistem — site 3 kez tamamen erişilemez oldu, 3 `aws ec2 reboot-instances` gerekti). Tetikleyici: art arda birden fazla main merge'i (kısa aralıklarla, hatta CONCURRENCY LOCK varken bile TEK BAŞINA bir deploy). **Reboot CPU credit'i DOLDURMAZ** — sadece o anki donmuş process state'ini temizler, kök nedeni çözmez. Ara-önlem (build+health-check penceresinde Prometheus/Grafana/Loki/Promtail'i geçici durdurmak, PR #124) yeterli göründü ama garanti değil — gerçek kalıcı çözüm build'i EC2 dışına taşımak (bkz. YOL HARİTASI madde 28). Deploy sonrası site'ın gerçekten dış dünyadan erişilebildiğini (`curl` timeout DEĞİL) doğrulamadan "deploy başarılı" deme — GitHub Actions'ın "Success" demesi bile SSM komutunun tamamlandığı anlamına gelir, reboot ARADA gerçekleşmişse container'lar ESKİ image'da kalmış olabilir (`docker exec <container> grep <yeni-kod-izi> <dosya>` ile doğrula).
- **"Güvenlik araştırmacısı" / beg-bounty maili gelirse (12 Eyl 2026'da yaşandı):** panik yok, önce nginx logunda (`docker logs nexstream_nginx --since 336h`) `/api/auth/login` 401/429 yığını, `/api/docs` referer'lı denemeler, negatif ID'ler, `source=%27` gibi SQLi tırnakları ve `/api/subscriptions/` POST'larıyla IP'yi bul; DB'de o IP'nin açtığı hesapları (`users.created_at` nginx zaman damgasıyla birebir eşleşir) ve `contact_messages`'ı kontrol et. Mail kalıbı: detay yok + aciliyet + "daha önce yazmıştım" (form boşsa yalan) + "teslim sürecini netleştirelim" (=ücret). Cevap: ödül programı yok (`/security`), rapor gönderirse değerlendirilir, pazarlığa girilmez. Repo PUBLIC olduğu için "statik kod analizi" iddiası normaldir.
- **`gh pr merge --auto` main'de zorunlu status check OLMADIĞI için ANINDA merge eder, testlerin bitmesini BEKLEMEZ** — 12 Eyl 2026'da 3 PR'da bu yüzden 2 deploy art arda kuyruğa girdi (concurrency lock çakışmayı önledi ama t3.small'da art arda deploy riskli, bkz. CHANGELOG 11 Eylül dersi). `--auto` KULLANMA; dal testinin yeşil olduğunu gördükten sonra elle `gh pr merge --squash` çalıştır ve bir sonraki PR'ı bir öncekinin deploy'u bitmeden merge etme.
- **Bülten uçları artık kimlik doğrulamalı (12 Eyl 2026):** `POST /subscriptions/` ve `DELETE /subscriptions/{email}` → X-API-Key VEYA e-postası eşleşen oturum (POST ayrıca `email_verified` ister, owner muaf). Mail içindeki iptal linki `email`+`token` (HMAC-SHA256, `adapters/api/subscription_tokens.py`, secret `UNSUBSCRIBE_TOKEN_SECRET` boşsa `API_KEY`) — imzasız link aboneliği KAPATMAZ. `API_KEY` rotasyonu eski maillerdeki iptal linklerini kırar; önce `UNSUBSCRIBE_TOKEN_SECRET`'ı eski API_KEY değerine sabitle.
- **Kullanıcı API anahtarı DB'de SHA-256 hash olarak saklanıyor (12 Eyl 2026)** — `UserRepository.set_api_key` ham anahtarı hash'ler, `get_by_api_key` ham anahtarı hash'leyip arar, `GET /account/api-key` ham değeri ASLA dönmez (sadece `has_api_key`). Anahtar üretim yanıtında BİR KEZ görünür. Yeni bir "anahtarı göster" özelliği eklemeye kalkma — elimizde yok.
- **`/api/metrics` nginx'te `location = /api/metrics { return 404; }` ile dışarıya KAPALI** — Prometheus iç ağdan `app:8000/metrics` okuyor. Yeni bir iç-servis endpoint'i (health hariç) eklerken aynı soruyu sor: dışarıdan görünmesi gerekiyor mu?
- **`frontend/public/.well-known/security.txt` `Expires: 2027-09-01`** — RFC 9116 geçmiş tarihi geçersiz sayar, `tests/infrastructure/test_security_txt.py` o tarihten sonra KIRMIZIYA döner; Ağustos 2027'de tarihi ileri al. Politika metni `frontend/lib/legal-content.ts::SECURITY_POLICY`, sayfa `/security`.
- **Cloudflare proxy'si origin'i SADECE Security Group 80/443'ü Cloudflare IP'lerine kısıtlarsa korur** — aksi halde origin IP'ye doğrudan istek Bot Fight Mode/WAF/rate-limit'i atlar (bkz. YOL HARİTASI madde 29). `set_real_ip_from` sadece IP'yi doğru okumak içindir, erişimi kısıtlamaz.
- **Sahip e-postası public repo'da 267 commit'in author alanında açık (`git log --format=%ae`, GitHub commits API)** — "güvenlik araştırmacısı" adresi büyük ihtimalle buradan aldı. 12 Eyl 2026'dan itibaren bu repo'da `git config user.email 76664196+MaviMakumba@users.noreply.github.com` (yeni commit'ler noreply ile gider); GitHub → Settings → Emails'te "Keep my email addresses private" + "Block command line pushes that expose my email" KULLANICI tarafından açılmalı. Geçmişteki 267 commit'i temizlemek `git filter-repo --mailmap` + force push + tüm SHA'ların değişmesi demek (21 Ağu'daki gibi) — kullanıcı kararı, henüz YAPILMADI. Tracked dosyalarda düz metin adres YASAK (`test_owner_email_not_in_tracked_docs`), Grafana alert adresi `.env`'deki `GRAFANA_ALERT_EMAIL`'den gelir (prod'da zorunlu, `:?`).
- **Sadece `.md`/`docs/**` değişen main push'ları CI'ı ve deploy'u HİÇ tetiklemez** (`paths-ignore`, 12 Eyl 2026) — dokümantasyon PR'ı merge edince "deploy olmadı" diye şaşırma; PR tetikleyicisi paths-ignore'suz, testler PR'da yine koşar.
- **Prod diskini BuildKit build cache sessizce doldurur** — 12 Eyl 2026'da 77GB diskin %80'i doluydu, `docker system df` 50GB build cache (49GB reclaimable) gösterdi; `docker builder prune --filter until=48h -f` ile 31GB geri alındı (%42), son deploy'ların katmanları korundu (tam `prune -af` sonraki build'i sıfırdan yapar, t3.small'da RAM/süre riski + pip hash gotcha'sı). Her birkaç haftada bir SSM ile `df -h /` + `docker system df` kontrol et, %70'i geçtiyse aynı filtreli prune'u çalıştır.
- **Grafana nginx arkasında sub-path'te: `proxy_pass $grafana_upstream;` URI PARÇASIZ olmalı ve `GF_SERVER_ROOT_URL=${FRONTEND_URL}/grafana/` sabit domain'li olmalı** (13 Eyl 2026'da iki bug üst üste bulundu: `%(domain)s` yer tutucusu localhost'a çözülüyordu, sonra sondaki `/` öneki silip sonsuz 301 döngüsü yaratıyordu). `curl -sI https://nexstreamnews.com/grafana/` → 302 `/grafana/login` beklenir; `localhost` ya da kendine 301 görürsen bu ikisine bak. Regresyon testleri `tests/infrastructure`.
- **"Adam GitHub'ı nereden buldu?" → `/api/docs` (Swagger) sayfasının açıklaması ve `openapi.json` `contact`/`license` alanları repo linkini içeriyor** (footer "API Docs" → oraya). Bilinçli (self-serve API portalı) — kaldırılmadı, ama repo linki = commit e-postası zinciri olduğunu bil.
- **Otomatik saldırgan engelleme kapsamı:** nginx `limit_req_zone` + slowapi endpoint limitleri sadece YAVAŞLATIR/429 döner, kalıcı bir IP ban/WAF/fail2ban YOK (Cloudflare geçişi bunu değiştirebilir, bkz. YOL HARİTASI madde 6). Kullanıcı bazlı banlama AYRI ve VAR (`PATCH /admin/users/{id}/active`) ama IP değil hesap seviyesinde.
- **`nexstream-deploy` IAM kullanıcısı AdministratorAccess DEĞİL** — `NexStreamDeployMinimal` policy'sine scope'landı (sadece EC2 describe/start/stop/reboot + SSM, `i-0608c897a3d8ca3f3` ile sınırlı). Başka bir AWS eylemi (S3, IAM, RDS, Budgets dahil) bu kimlikle YAPILAMAZ, kullanıcıya sor.
- **v1.11 sonrası yeni env var'lar:** güncel/tam liste `docker-compose.prod.yml` + `settings.py`'de — hangi versiyonda eklendiğinin kronolojisi CHANGELOG'da.
- **v2.0 nginx dersi:** `upstream` blokları AÇILIŞTA çözülür — tek bir upstream host'u ayakta değilse nginx HİÇ açılmaz. Opsiyonel/ikincil upstream'ler (grafana gibi) değişkenli `proxy_pass` + `resolver 127.0.0.11` ile lazy çözümlenmeli. `app`/`frontend` bilinçli olarak sabit upstream (zaten zorunlu).
- **v2.0 Next.js standalone dersi:** Docker'ın otomatik koyduğu `HOSTNAME=<container-id>` Next.js standalone `server.js`'i TEK bir ağ arayüzüne bind eder — container iki ağdaysa nginx diğer ağdan ulaşamaz (502). `frontend/Dockerfile`'da `ENV HOSTNAME=0.0.0.0` şart.
- **v2.0 ChromaDB imaj dersi:** bu imajda `curl`/`wget`/`python`/`nc` YOK, sadece `bash` — healthcheck `/dev/tcp` ile elle kurulmalı. `/api/v1` kaldırıldı, `/api/v2` kullan.
- **Resend sandbox kısıtı:** doğrulanmış bir domain yoksa sadece hesap sahibinin KENDİ e-postasına gönderim yapılabilir (403, sessizce loglanır).
- **Prod DB adı `nexstream`, `nexstream_db` DEĞİL** — `docker exec nexstream_db psql -U nexstream -d nexstream`.
- **Rol ve tier BAĞIMSIZ eksenler:** `ADMIN_EMAILS` bootstrap'i sadece `role`'ü etkiler, `tier`'a dokunmaz — "admin ama Ücretsiz kullanıcı" normaldir.
- **Sessiz veri kaybı deseni:** "kaydet → sonra ID'ye ihtiyaç duyan bir şey yap" akışı eklerken ORM nesnesinin PK'sının domain nesnesine gerçekten geri yazıldığını (`refresh()`+atama) doğrula — exception fırlatmaz, sadece alan `None` kalır (`user_repository.py::create_user` doğru pattern).
- **Env-var tabanlı yetki bootstrap'ı (`ADMIN_EMAILS`/`OWNER_EMAILS`) sadece kayıt sırasında email normalize edilirse güvenlidir** — `register()`'ın da lookup ile AYNI normalizasyonu (strip+lowercase) uniqueness kontrolünden ÖNCE yapması gerekir, yoksa case-varyantı farklı bir satır yaratıp yine de env eşleşmesinden geçebilir.
- **Bir dosyada `user.tier`'ı `effective_tier`'a çeviren bir görev bittiğinde, o dosyada kalan TÜM `user.tier` okumalarını grep'le taramadan "bitti" deme** — final whole-branch review'a kadar unutulabilir.
- **Local ve prod AYNI paylaşılan `GROQ_API_KEY`'i kullanıyor** — local'de worker/scheduler'ı uzun süre açık bırakmak prod'un GÜNLÜK bütçesini paylaşıp tüketir. Uzun local test yapacaksan ayrı bir key kullan ya da test kısa tut, sonra **mutlaka `docker compose down`**.
- **Türkçe ek kırpma (`_stem_tr`) substring bug'ı:** eşleşme kelime BAŞINA sabitli olmalı (`\bterim` regex) — ham `in`/substring kontrolü "Adana" aramasının "havadan"ın ortasında eşleşmesi gibi alakasız sonuçlar verir.
- **Tek instance'lık background task + çoklu uvicorn worker = sessiz duplikasyon:** `lifespan`'de `asyncio.create_task` ile başlatılan HER job prod'da `--workers 2` yüzünden İKİ AYRI PROCESS'te kopyalanır. Yeni bir "günde bir kez, yan etkili" job eklerken idempotent olduğunu KANITLAMADIKÇA `pg_try_advisory_lock` deseni gerektiğini varsay (bkz. `newsletter_job.py`).
- **Bir metrik/rozet iki farklı yerde iki farklı ALGORİTMA ile hesaplanırsa tutarsızlık garanti** — aynı veriyi gösteren iki UI elemanı (sayı + liste, özet + detay) varsa altlarındaki hesaplamanın AYNI fonksiyonu paylaştığını doğrula.
- **Entity-overlap tabanlı bir eşleştirmede "kaç entity paylaşılıyor" tek başına yeterli sinyal değil — HANGİ entity'ler paylaşılıyor da önemli.** Bir yerde bulunan entity-overlap sinyal-kalitesi bug'ı, aynı mekanizmayı kullanan kardeş modüllerde de neredeyse KESİN vardır — kod genelinde tara (`grep _entity_name_set/_entity_name_map`), "orada kanıt yok" diye atlama. Ortak yardımcı: `_distinguishing_entity_keys`.
- **Emoji glifin rengi CSS `color` ile kontrol edilemez** — ikon-only/az metinli aksiyon butonlarında `.icon-chip` class'ını kullan (hafif zemin+kontur+`var(--text2)`), çıplak emoji + inline renk KULLANMA.
- **Resmi olmayan/üçüncü parti bir API'ye yeni bir sembol/endpoint eklerken mock testler geçse bile en az bir kez gerçek bir çağrı (curl/WebFetch) ile doğrula** — mock'lu testler geçersizliği YAKALAMAZ.
- **Bash aracının otomatik izin sınıflandırıcısı artık `gh`/`aws ssm`/`aws ec2` komutlarını engellemiyor** (24 Ağu 2026'da düzeldi) — önceki bir oturumda engellenmiş olması bir daha engelleneceği anlamına gelmez, önce dene.
- **Public bir endpoint'in "cache miss" yolu pahalıysa (dış API çağrısı), negative-cache-on-failure şart** — başarısızlıkta son iyi değeri kısa TTL'li olarak TAZE cache anahtarına da yaz, yoksa dış kaynak kesikken her istek yeniden pahalı çağrı dener.
- **🔒 21 Ağu 2026'da git geçmişi mahremiyet gerekçesiyle yeniden yazıldı** (Claude attribution satırları kaldırıldı, SHA'lar değişti) — rewrite'tan önce klonlayan biri varsa onun kopyasında eski SHA'lar kalıcı olarak durur. Global `~/.claude/settings.json`'da attribution artık kapalı, tekrar gerekmiyor. Detay: CHANGELOG.
- **24 Ağu 2026 telif hakkı değerlendirmesi — düşük risk, tek şart:** her kartta kaynak gösterimi (isim+tarih+link) doğru/görünür kalmalı, tam makale metni saklama kararına (madde 18) SADIK kalınmalı. Detay/hukuki gerekçe: CHANGELOG.
