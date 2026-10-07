# NexStream News Engine — Yol Haritası (tam metin + arşiv)

CLAUDE.md'deki "YOL HARİTASI" bölümü 7 Ekim 2026'da ~350 satıra şişince buraya taşındı (birebir, numaralar korundu).
CLAUDE.md artık yalnız AÇIK işleri tek satırla tutar; bir madde tamamlanınca burada ✅ işaretle.
Tamamlanan işlerin kronolojik anlatısı ayrıca `docs/CHANGELOG.md`'de.

---

## YOL HARİTASI (kalan işler)

Tamamlanan işlerin tam kronolojik dökümü `docs/CHANGELOG.md`'de. Burada sadece
GERÇEKTEN bekleyen işler var:

0. **📋 HER OTURUM BAŞINDA: `docs/DURUM-DEGERLENDIRMESI.md`'deki öncelik
   tablosunu kullanıcıyla gözden geçir** (28 Eyl 2026 SWOT + ölçümler + elimizde
   olan/olmayan + fazlalar + aciliyet sıralı iş listesi — kullanıcı isteği:
   "sonraki oturumlarda mutlaka değinelim, kaybolmasınlar"). Tamamlanan satırı
   orada işaretle, silme. Özet (28 Eyl):
   - 🔴 **Sunucu/bütçe kararı** — AWS kredisi ~Kasım 2026 ortası biter;
     Hetzner CX33 taşıma planı+provası **Ekim başında** başlamalı.
   - 🔴 **R2 offsite yedek** — kullanıcı CF'de bucket `nexstream-backups` +
     bucket-scope'lu Object R/W token açıp anahtarları verecek.
   - 🔴 **Yedekten geri yükleme testi** — hiç yapılmadı (taşımayla birleştir).
   - 🟠 28 Eyl değişikliklerini izle (qwen kalite/kota, 03:00 yedeği, Chroma
     rollback kopyasını sil), Dependabot toplu (16 PR), #28 GHCR, #30.
   - 🟡 #14, #13, yeni kaynaklar, `api.ts` yolu, `_stem_tr`, #26.
   - 🟢 Launch/AdSense/Reddit, #18, #3, #2.
   - **30 Eyl 2026 güncellemesi:** 🟠 izleme ✅, Dependabot ✅ (#174→release), #30 ✅, #28 GHCR **şimdilik gereksiz** (18 Eyl'den beri host sağlıklı); 🟡 #14 ✅ (özet yankısı UI'da gizlendi — kök neden kaynağın RSS'inde açıklama olmaması), #13 ✅ (özel isim doğrulaması), `api.ts` yolu ✅, `_stem_tr` ✅, #26 (`/contact` maili) **teyit bekliyor**; 🟢 AdSense ön hazırlığı (çerez kategorileri) + Product Hunt taslağı ✅ (`docs/launch/`). **HÂLÂ AÇIK 🔴:** sunucu/bütçe kararı (Kasım ortası!), R2 offsite yedek (kullanıcı token verecek), yedekten geri yükleme testi.
   - **İçerik/tazelik/çok dillilik yol haritası (B+D, kullanıcı onaylı spec):** S1 ✅ S2 ✅ (30 Eyl deploy); **sıradaki S3** (raf ömrü `shelf_life`→`expires_at`, feed filtresi, aciliyet-farkındalıklı arama/RAG: "altın fiyatı" → bugünün haberi, 3 gün önceki maç yayın haberi timeline'da görünmesin), **S4** (iki dilli başlık/özet — analiz çağrısında çeviri, `lang` API, "çevrildi" rozeti), **S5** (çapraz dilli arama/RAG: "iklim değişikliği" ↔ "climate change"). **S6 (eski haber çevirisi) İPTAL** — kullanıcı kararı, yalnız yeni haberler. Planlar: `docs/superpowers/plans/`. Sonra **C** (filtre/liste UI yenilemesi, mobil-önce).

1. ~~Anasayfa tasarım yenilemesi~~ — ✅ 18 Eylül 2026 (PR #155). `frontend-design`
   skill'iyle brainstorm edildi: Day teması (varsayılan) kırmızı vurgu +
   Newsreader serif kimliğine yenilendi — **tema seçici hâlâ anasayfayı da
   kapsıyor** (kullanıcı bilinçli kararı: "temalar değiştikçe sayfanın
   değişmesi güzel bir özellik, kalsın" — bu yüzden yeni palet ayrı bir
   sayfa-scope class'a değil doğrudan `[data-theme="day"]`'e yazıldı, diğer
   9 tema ve dashboard/admin etkilenmedi). Hero'ya gerçek `/feed.xml`'i
   çeken bir canlı akış paneli (`LiveWireStrip.tsx`, Pro-özel WebSocket
   yerine public RSS poll — anonim ziyaretçide paywall göstermesin diye)
   ve yeni "Bir haber kartında neler var?" bölümü (`CardSpotlight.tsx`,
   Kaydet/Güvenilirlik skoru/Sor/Dinle/İlgili haberler/Habere git numaralı
   pin'lerle işaretli — kullanıcı geri bildirimi: ziyaretçiler bu
   özellikleri fark etmiyordu) eklendi. Aynı oturumda bulunan iki bug da
   düzeltildi: Navbar aktif-sekme prefix-match çakışması (Haberler/Arama/
   Soru Sor aynı anda aktif görünüyordu) ve `/dashboard/ask`'ın mount'ta
   gereksiz `scrollIntoView` ile sayfayı kaydırması. **Deploy sonrası
   kullanıcı bulgusu (PR #157):** anasayfadaki Bülten/Ham Veri Export
   kartları `/account`'a düz gidiyordu, sayfanın tepesinde açılıyordu —
   ilgili `.card`'lara `id="newsletter"`/`id="export"` +
   `scrollMarginTop` eklendi, link'ler `#newsletter`/`#export`'a
   güncellendi (Export sadece Enterprise'da render edildiği için diğer
   tier'larda hedef yok, tarayıcı tepede kalır — regresyon değil). **Footer
   artık paylaşılan bir bileşen** (`components/Footer.tsx`) — sadece
   anasayfada değil, /privacy /terms /security /contact'ta da var (kullanıcı
   bulgusu: arama motorundan bu sayfalara doğrudan gelen ziyaretçinin siteyi
   keşfetme yolu yoktu). Bilinçli olarak dashboard/hesabım/admin ve auth
   (giriş/kayıt) ekranlarına EKLENMEDİ — ilki uygulama-içi yoğun ekran,
   ikincisi odaklanma gerektiren minimal ekran (Stripe/Linear deseni).
   **E-posta şablonları da yenilendi** (`email_adapter.py::_brand_shell`,
   kullanıcı bulgusu: "bülten/şifre/anlık maillerin içeriği eski ve sade
   kaldı, siteye git gibi linkler yok") — tüm kullanıcı-görünür mailler
   (digest/alert/reset/verify/welcome) artık aynı NexStream başlığı + footer'da
   her zaman "Siteye git", digest/alert'te ayrıca "Aboneliği iptal et"
   paylaşıyor. Renkler CSS `var()` DEĞİL düz hex (e-posta istemcileri custom
   property okumaz) — Day temasının paletiyle (`#c31e2a` vb.) elle senkron,
   yeni bir marka rengi değişikliğinde `_brand_shell`'i de güncellemeyi
   unutma.
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
    doğruluk kaynağı yapıldı. **3. dilim ✅ 28 Eyl 2026 (PR #169):**
    pacing YETMEDİ — bağlayıcı limit TPD çıktı (Prometheus: 24 saatte ~250K
    token, 702×429; RPD/TPM rahattı) ve model havuzu 429'da diğer modele
    geçmeyip aynı modelde ~200 sn uyuyordu (qwen fiilen boştu). Artık 429
    alan model soğumaya alınıp istek hemen havuzdaki diğerine gidiyor.
    Near-duplicate kontrolü zaten analizden ÖNCE çalışıyor (eski not
    yanlıştı). **Sonraki iş:** birkaç gün `nexstream_groq_tokens_total`'ı
    model bazında + 429 sayısını + worker tur süresini izle; qwen analiz
    kalitesini (sentiment dağılımı, boş özet oranı) 20b ile karşılaştır.
    Kapasite yine yetmezse sıradaki kaldıraç: çağrı başına token (~517).
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
28. ~~**Deploy build'ini EC2 dışına (GitHub Actions runner'ına) taşımak**~~ — ✅ **7 Eki 2026 (PR #199, canlıda doğrulandı, deploy ~3,5 dk).** Aşağıdaki metin tarihçedir: **Deploy build'ini EC2 dışına (GitHub Actions runner'ına) taşımak —
    11 Eylül 2026'da t3.small'ı üç kez tamamen tıkayan (SSM Agent bile
    yanıt veremedi, 3 reboot gerekti) prod kesintisinin GERÇEK kalıcı
    çözümü.** Kök neden `docker compose up --build -d`'nin EC2 üzerinde
    hem build hem 16 container'ın recreate'ini aynı anda yapması — anlık
    RAM/CPU darboğazı yaratıyor (embedder gibi RAM-ağır bir servisin ESKİ
    ve YENİ kopyası kısa süre aynı anda bellekte kalabiliyor). Image'ı
    GitHub Actions runner'ında build edip ücretsiz bir registry'ye (GHCR)
    push etmek, EC2'nin sadece `docker pull`+`up -d` yapmasını sağlar —
    build hiç EC2'de olmaz. **Ara-önlem (PR #124, 11 Eylül) TEK BAŞINA
    YETERSİZ olduğu 18 Eylül 2026'da KANITLANDI:** izleme yığını
    (Prometheus/Grafana/Loki/Promtail) build sırasında zaten durdurulmuş
    haldeyken bile (mitigation aktifti, doğrulandı) tek bir frontend+backend
    değişikliği içeren normal bir deploy'da load average 24'e, swap
    kullanımı 2.0Gi'nin tamamına çıktı; `nexstream_engine`/`embedder`/
    `redpanda` sırayla unhealthy/OOM oldu, site ~20 dakika 10+ saniyelik
    yanıt süreleriyle fiilen kullanılamaz durumdaydı (SSM Agent bu sefer
    "Online" kaldı, komutlar sadece çok yavaştı — 11 Eylül'deki gibi tam
    kopma olmadı ama aynı kök neden). Sistem ~20 dakika sonra KENDİ
    KENDİNE toparlandı (reboot'a GEREK KALMADI — reboot denemesi zaten
    Claude Code'un otomatik izin sınıflandırıcısı tarafından iki kez
    reddedildi, "Production Deploy"/"dangerous" gerekçesiyle; kullanıcı
    onayı bunu AŞAMADI, gerçek reboot ancak kullanıcının kendi AWS
    Console/CLI erişimiyle mümkün). **Kullanıcı CPU Credit "Unlimited"
    moduna geçmeyi bilinçli REDDETTİ** (küçük de olsa bir maliyet riski
    istemedi) — bu yüzden registry'ye taşıma tek gerçek "$0 garantili"
    kalıcı çözüm, artık ERTELENEMEZ. Bounded değil, ayrı bir tasarım/plan
    turu gerektirir (registry auth, image tagging/versioning, workflow
    yeniden yazımı). **Bu maddeye kadar geçici disiplin: küçük/acil
    olmayan değişiklikleri tek tek deploy etmek yerine biriktirip TEK
    seferde göndermek** (kullanıcı kararı, 18 Eylül) — her `main` push'u
    EC2'de tam bir `--build` tetikliyor, sık push = sık RAM/CPU spike'ı.
    Detay: CHANGELOG "11 Eylül prod kesintisi", "18 Eylül deploy yavaşlaması".

29. ~~**Security Group sıkılaştırma + duckdns kapatma**~~ — ✅ **13 Eyl 2026.**
    Kullanıcı `nexstream-deploy` IAM kullanıcısına inline policy
    `NexStreamSecurityGroupEdit` (DescribeSecurityGroups/Rules `*`,
    Authorize/RevokeSecurityGroupIngress sadece `sg-061424eb4ff9eb775`) verdi;
    Claude SG'yi düzenledi: **22 kapalı** (SSM ile bağlanıyoruz), **80/443 sadece
    Cloudflare IPv4 (15) + IPv6 (7) aralıklarına açık** (`cloudflare.com/ips-v4`
    + `ips-v6`, nginx `set_real_ip_from` listesiyle aynı). Sıra: önce CF
    aralıkları eklendi → site doğrulandı → `0.0.0.0/0` kuralları kaldırıldı
    (kesintisiz). Doğrulama: CF üzerinden 200, origin IP'ye doğrudan 80/443
    timeout, 22 filtered, SSM çalışıyor. duckdns subdomain'i kullanıcı sildi
    (NXDOMAIN), sertifika zaten duckdns SAN'sız. **Cloudflare IP listesi
    değişirse** hem `nginx.conf` hem SG güncellenmeli — ikisi de aynı listeyi
    taşıyor; `aws ec2 describe-security-groups --group-ids sg-061424eb4ff9eb775`
    ile karşılaştır. Let's Encrypt yenilemesi CF proxy üzerinden 80'e gelir
    (CF aralıkları açık), 443 bloğunda da ACME webroot var.
    - Kalan (kullanıcıda): GitHub → Settings → Emails gizlilik kutuları; 3.
      parti hesaplarda MFA (AWS root+IAM, Cloudflare, GitHub, domain kayıt,
      Resend, Groq, Gmail).
    - **Sunucu büyütme (t3.medium) BİLİNÇLİ YAPILMADI** (13 Eyl): build cache
      temizliği sonrası host rahatladı, kullanıcı krediyi korumak istiyor;
      RAM/CPU-credit sorunu tekrar yaşanırsa `ec2:ModifyInstanceAttribute`
      izniyle stop→tip değiştir→start (5 dk kesinti) ya da Hetzner kararı.

30. **Güvenlik günlüğü (security_events) sekmesinin tam denetimi — 18 Eylül
    2026'da kullanıcı isteğiyle açıldı, HENÜZ YAPILMADI.** Tetikleyici:
    kullanıcı hesap silmenin (`DELETE /account`) günlükte hiç görünmediğini
    fark etti — bu TEK eksik aynı gün bounded bir düzeltmeyle kapatıldı
    (`EventType.ACCOUNT_DELETED`, TDD, `account_router.py::delete_account` +
    `admin/security/page.tsx::EVENT_TYPES`). Ama kullanıcının asıl isteği
    daha genişti ("sekmeyi iyice bir elden geçirmek lazım") — bu, o anda
    oturum zaten çok uzadığı (aynı gün: anasayfa yenileme + mobil responsive
    turu + footer + e-posta şablonları + bir prod yavaşlaması) için AYRI/TAZE
    bir oturuma ertelendi, ama kullanıcı "erteleme dediğin iş kayboluyor"
    diye haklı bir kaygı belirtti — bu yüzden burada AÇIK bir madde olarak
    duruyor, sözle geçmedi. **Sonraki oturumun işi:** mevcut 15 `EventType`'ın
    (artık ACCOUNT_DELETED dahil) kullanıcı yaşam döngüsünün geri kalanını
    (bülten aboneliği/iptali, kaydedilen haber, push bildirim aboneliği gibi
    güvenlik-ilişkisiz olanlar HARİÇ tutulmalı — hepsini eklemek gürültü
    yaratır) gerçekten kapsayıp kapsamadığını sistematik gözden geçir; ayrıca
    `/admin/security` sayfasının kendisinin (filtre UX'i, sayfalama var mı,
    IP/e-posta çapraz sorgulama akışı) kullanıcı gözünden hâlâ yeterli olup
    olmadığını sor.

31. **Sunucu disk/log hijyeni + CI sağlamlığı (7 Eki 2026 akşamı bakıldı, HENÜZ YAPILMADI — kullanıcı onayı bekliyor):**
    - Otomatik temizlik ZATEN var: `deploy_images.sh` son 3 başarılı sha'yı tutar, gerisini + dangling imajları siler (disk %42, dangling 0).
    - **Build cache 16,8 GB hepsi geri alınabilir** (build artık CI'da, EC2'de büyümüyor): `docker builder prune -af`. Tek bedel: acil yerel build'in ilk seferde sıfırdan başlaması.
    - **`nexstream_loki` container logu 908 MB, rotasyon YOK** (compose'ta `json-file` `max-size` yok). Kalıcı çözüm: yalnız Loki servisine `max-size: 10m`/`max-file: 3` + Loki `log_level: warn` (compose değişikliği sadece Loki'yi yeniden oluşturur). TÜM servislere birden rotasyon ekleme: 16 container birden recreate olur, t3.small'da risk. Nginx logu (62 MB) yavaş büyüyor, sonra.
    - **Swap 1,5/2 GB (%73) dolu**, RAM'de ~500-600 MB boş — şimdilik sorun yok ama yeni RAM yükü sınırı zorlar (Hetzner kararı bunu da çözer).
    - **CI `frontend` job'u "Install Playwright Chromium" adımında saatlerce asılabilir** (7 Eki: 44 dk, deploy bu job'a bağlı olduğu için bekledi). Çözüm: `gh run cancel <id>` → bitince `gh run rerun <id>`; kalıcı çözüm adıma `timeout-minutes` ya da Chromium önbelleği (ayrı PR).
    - RAG token tüketimi artık ölçülüyor (`nexstream_rag_tokens_total`), soru başına ≈2K token → 120b'deki ~50K/gün RAG payı ≈24 soru. Sorgu genişletici de 120b kullanıyor ve token'ı hâlâ ÖLÇÜLMÜYOR.

### Kasıtlı Kapsam Dışı (fayda/maliyet uygun değil)
K8s/Helm, Qdrant migration, CQRS, NTV Playwright scraper, Twitter/X entegrasyonu,
custom (Stripe dışı) billing portalı, App Store/Play Store (sadece PWA)

---
