# İçerik genişletme, çok dillilik ve tazelik-öncelikli akış — Tasarım

**Tarih:** 29 Eylül 2026 · **Durum:** kullanıcı incelemesi bekliyor · **Yol:** mimari (spec → plan → uygulama)
**Kapsam:** yol haritası "B" (konu + kaynak genişletme) + kullanıcının aynı oturumda eklediği iki
gereksinim (çok dilli içerik, tazelik önceliği). Üçü aynı analiz prompt'una ve aynı veri
modeline dokunduğu için tek tasarım, dilimlenmiş uygulama.

## 1. Amaç ve başarı ölçütleri (kullanıcının sözleriyle)

1. **Tazelik en önemli faktör.** "En güncel haberler sürekli en üstte kalsın. 3 gün önceki maçın
   hangi kanalda olacağı haberi timeline'da gözükmesin. Altın fiyatı sorulunca bu günkü altın
   fiyatı haberi gelsin, soru sor kısmında da."
2. **Dil tutarlılığı.** Arayüz Türkçeyse tüm haberler Türkçe, İngilizceyse İngilizce sunulur
   (başlık, açıklama, özet). Yabancı kaynaktan gelen ağır bir İngilizce makale Türkçe sayfada
   karmaşa yaratmasın; Türkçe haberlerin de İngilizcesi olsun (uluslararası olmak).
   "Daha fazlası için kaynağa git" — kaynak sitenin kendi çevirisi bizi bağlamaz.
3. **Çapraz dilli arama/RAG.** "climate change" haberi varken "iklim değişikliği ne durumda"
   sorusu cevapsız kalmasın.
4. **Dengeli portföy.** Konu başına kaynak sayısı dengeli olsun (5 spor + 1 bilim + 10 magazin
   olmasın); yeni konular: **Bilim, Kripto, Çevre & İklim, Eğlence**.
5. **Sürdürülebilirlik.** Groq ücretsiz kotası ve t3.small RAM'i aşılmayacak; ölçülebilir olacak.

Başarı ölçütleri: (a) varsayılan timeline'da süresi dolmuş (perishable) haber yok; (b) "altın fiyatı"
aramasının ilk sonucu son 24 saatten; (c) TR arayüzde tüm kartlar Türkçe, EN'de İngilizce (çeviri
yoksa orijinal + belirgin işaret, alan asla boş değil); (d) "iklim değişikliği" sorusu EN kaynaklı
haberleri de kanıt olarak getirir; (e) 7 günlük konu dağılımında "Diğer" %22 → <%10, hiçbir konu
<%3; (f) günlük nötr-yedek (fallback) oranı ≤ %5.

## 2. Ölçülen mevcut durum (29 Eylül 2026, prod)

| Bulgu | Veri |
|---|---|
| Günlük hacim | 1044 haber/gün (17 kaynağın tamamı çalışıyor), 24 sa 551K token, 574×429, 40 nötr-yedek |
| Kapasite | Havuz (gpt-oss-20b + qwen) doygunluğa yakın; sabit üst sınır ≈ 1000-1100 analiz/gün |
| Çağrı başı token | prompt ≈ 320, completion ≈ 210 (reasoning dahil) |
| Konu dağılımı (7 gün, 4211 haber) | Politics %23,3 · **Other %22,3** · Sports %21,5 · Technology %14,4 · Economy %8,5 · Culture %5,7 · **World %2,7** · **Health %1,6** |
| Gürültülü kaynaklar (24 sa) | CNN Türk 194, Sözcü 161, Anadolu 147, TRT 126 |
| Özet yankısı | Özetlerin %22'si başlığı tekrarlıyor, kaynağın RSS'i açıklama vermediği için (PR #175 ile UI'da gizlendi) |
| Çapraz dil | `iklim değişikliği` → yalnızca TR sonuç; `climate change` → TR "iklim krizi" haberi 0,39 skorla (RAG eşiği 0,4 ve tazelik/güvenilirlik çarpanları altında) |
| Tazelik | Mevcut decay: 30 günlük pencere, taban 0,5 → 3 günlük haber 0,95 çarpanı alır, yani tazelik neredeyse hiç ayırt etmez |
| Sıralama | Sayfalı uç `id.desc()` idi (PR #171 ile yayın tarihine çevrildi) |
| Backlog işleme | Worker geride kalınca ESKİ haberleri de analiz ediyor (28 Eyl gözlemi) → kota tazeliğe değil eskiye gidiyor |

## 3. Dilimler (uygulama sırası; her dilim TDD, sonda tek deploy)

| Dilim | İçerik | Bağımlılık |
|---|---|---|
| **S1** | Konu kayıt defteri (12 konu) + prompt + `GET /api/v1/news/topics` + frontend/e-posta dinamik etiketler | — |
| **S2** | Tazelik-öncelikli alım (ingest) + kaynak portföyü + günlük tavanlar + yeni scraper'lar + topic metriği | S1 |
| **S3** | Tazelik: `shelf_life` → `expires_at`, feed filtresi, eski veri için kural tabanlı geçmiş doldurma, aciliyet-farkındalıklı arama/RAG sıralaması | S1 |
| **S4** | İki dilli içerik: şema, analiz sözleşmesi, `TranslationPort`, API `lang`, frontend + rozet, e-posta/RSS | S1 |
| **S5** | Çapraz dilli arama ve RAG (sorgu çevirisi, iki dilde anahtar kelime, çift dilli embedding metni) | S4 |
| **S6** | Eski 28 bin haber için lazy + bütçe-duyarlı arka plan çevirisi | S4 |

## 4. Tasarım

### 4.1 Konu kayıt defteri (S1)
- `src/domain/topics.py`: `TOPICS = (id, {"TR": ..., "EN": ...})`. 12 konu: Technology, Sports,
  Economy, Politics, Health, Culture, World, Other **+ Science, Crypto, Environment, Entertainment**.
- Tek doğruluk kaynağı: `VALID_TOPICS`, analiz prompt'unun konu listesi ve tanımları, e-posta
  etiketleri (`email_adapter`), abone tercih doğrulaması bu modülden türer. Frontend
  `TOPIC_VALUES`/`NEWSLETTER_TOPICS`/`TOPIC_LABELS` yerine `GET /api/v1/news/topics` okunur
  (SWR-benzeri önbellek; hata olursa gömülü yedek liste). Şimdi 5+ yerde elle kopya.
- Prompt'a her konu için **tek satırlık ayırt edici ipucu** (Crypto ≠ Economy, Entertainment ≠
  Culture, Environment ≠ Science) — "Other" kaçağını azaltır.
- Eski haberler eski konusuyla kalır (yeniden sınıflandırma token harcar); S6 arka plan işi
  sınıflandırmayı çeviriyle aynı çağrıda düzeltir.
- Abone `preferred_topics` alanı serbest string listesi olduğundan şema değişmez.

### 4.2 Tazelik-öncelikli alım ve portföy (S2)
- **Alım sırası:** scraper çıktısı `published_at` azalan sıralanır (BBC Health/Science/DW gibi
  feed'ler tarih sıralı değil; ilk-25 dilimi bayat haber alıyordu) ve `max_article_age_hours`
  (varsayılan 48) üstündeki öğeler **hiç analiz edilmez**. Kota darlığında en tazeler önce.
- **Kaynak günlük tavanı:** `Scraper` özniteliği `daily_cap` (+ `SOURCE_DAILY_CAPS` JSON env
  geçersiz kılması). `update_news_from_source`, `count_since(source, 24h)` ile kalan bütçeyi
  hesaplar; tavan dolunca **en taze olanlar alınmış olur** (sıra tazelik). Tavana çarpma
  `nexstream_source_capped_total{source}` sayacı ile görünür.
- **Kaynak meta verisi:** `language` (TR/EN) ve `focus_topic` (yoksa "general") registry'de.
- **Metrik:** `nexstream_articles_processed_total`'a `topic` etiketi (denge Grafana'dan izlenir).
- **Portföy (başlangıç; her feed eklenmeden önce canlı doğrulanır, alt ajan doğrulaması 29 Eyl):**

| Konu | Mevcut | Eklenecek | Not |
|---|---|---|---|
| Sports | BBC Sport, HT Spor, Hürriyet Spor | — | genel kaynaklarla zaten fazla; tavanlar düşer |
| Technology | BBC Tech, Guardian Tech, TechCrunch, HN, The Verge | AA Bilim-Teknoloji (TR) | TR teknoloji kaynağı yok |
| Economy | AA Ekonomi | **Dünya** (TR) | EN ekonomi adayı ayrıca test edilecek |
| Crypto | — | **CoinDesk**, **Cointelegraph** (prod'dan doğrulandı) | |
| World | BBC Türkçe (karma) | **Al Jazeera**, **DW** (tarih sırası düzeltmesi şart), TRT Haber Dünya | |
| Health | — | **BBC Health**, ScienceDaily (kısmen) | arz düşük; hedef pay buna göre |
| Science | — | **ScienceDaily**, AA Bilim-Teknoloji | NASA düşük hacim, sonra |
| Environment | — | BBC Science & Environment (bayat karışık, tarih sırası şart), Guardian Environment (test edilecek) | |
| Entertainment | — | BBC Entertainment & Arts | |
| Culture | — | **AA Kültür**, Guardian Culture | |
| Politics/General | TRT, CNN Türk, AA, Sabah, Sözcü, Hürriyet, Habertürk | — | tavanla ~%40 kısılır |

- Hedef günlük toplam ≈ **900-950** (çeviri token maliyeti sonrası kapasite, bkz. §5); genel
  kaynaklar için başlangıç tavanları: CNN Türk 120, Sözcü 100, AA 100, TRT 100, diğerleri 60-80;
  yeni kaynaklar 15-60. Değerler env ile ayarlanır, Grafana ile yinelenir.
- Reddit ve NPR elendi (429 / düşük hacim). `deployment_config` regresyon testi (prod compose ↔
  `settings.py`) yeni kaynak listesini de kapsar.

### 4.3 Tazelik: raf ömrü, feed ve arama (S3)
- **Analiz alanı `shelf_life`:** `short` (≤24 sa: program/yayın saati, fiyat, hava, canlı blog, baraj
  doluluk), `medium` (≤72 sa: günlük gelişme), `long` (süresiz). Prompt'ta 1 satır (+~5 token).
- **`expires_at` (nullable, `news_articles`):** `published_at + ömür`; `long` → NULL. Varsayılan
  feed (`GET /api/v1/news`, RSS, WS canlı akış, bülten) `expires_at IS NULL OR expires_at > now()`.
  Arama süresi dolmuşu **bulur** ama tazelik çarpanıyla en alta iter; `include_expired=true` ile
  arşiv görünümü. Silme yok (telif/kaynak kaydı korunur).
- **Geçmiş doldurma (LLM'siz):** kural tabanlı SQL — başlıkta `hangi kanalda|saat kaçta|maç
  özeti|canlı|doluluk oranı|hava durumu|fiyatı|kaç TL|kaç lira` → `expires_at = published_at+48h`.
- **Aciliyet-farkındalıklı arama/RAG:** sorgu sezgisi (`fiyat|kur|bugün|şimdi|saat kaçta|hangi
  kanalda|son dakika|price|today|live|now`) → **keskin tazelik**: decay yarı-ömrü saat mertebesi
  (varsayılan pencere 30 gün / taban 0,5 yerine 48 sa / taban 0,05). Diğer sorgularda mevcut yumuşak
  decay korunur. RAG kanıt paketi tazelik sırasına göre dizilir; aynı hikâyenin (story cluster)
  eski güncellemeleri en yeniyle değiştirilir; prompt'a **bugünün tarihi** verilir ve "zamana
  duyarlı soruda en yeni kaynağı kullan, eskiyse söyle" kuralı eklenir.
- Ölçüt testi: "gram altın fiyatı" sorgusu, bir gün eski ve bugünkü iki haber arasında bugünküyü
  1. sıraya koyar (birim test + prod duman testi).

### 4.4 İki dilli içerik (S4)
- **Depolama:** `news_articles.title_i18n JSON`, `summary_i18n JSON` (`{"TR": ..., "EN": ...}`) +
  `source_lang` ("TR"/"EN", kaynağın registry dilinden). Orijinal `title`/`summary` alanları
  değişmez (geriye uyumluluk, kaynak atfı). Çeviri yoksa ilgili anahtar yoktur.
- **Analiz sözleşmesi (tek çağrı):** yanıt JSON'una `title_alt`, `summary_alt` (kaynağın *karşı*
  dilinde), `shelf_life`; **`sentiment_label` prompt'tan çıkarılır** (skordan türetiliyor, PR #173).
  Beklenen token etkisi: +~70 completion, −~20 prompt/completion → net ≈ +%7. Ayrıştırıcı: alt
  alan yoksa/geçersizse `None` (çeviri eksik ≠ analiz hatası; entity/topic/sentiment yine kaydedilir).
- **`TranslationPort` (hexagonal):** `translate(text, source_lang, target_lang)`; ilk uygulama
  "analiz çağrısına gömülü" (port yalnızca lazy/backfill yolu için Groq'la çalışır). İleride
  yerel MT (CTranslate2/opus-mt, Hetzner sonrası) aynı porta takılır — kota bağımsız.
- **API:** `lang` sorgu parametresi (`TR|EN`, varsayılan orijinal). `NewsResponse`: `title`/`summary`
  seçilen dilde, `original_title`, `original_lang`, `translated: bool`. Frontend her istekte
  `settings.lang` gönderir. Çeviri yoksa orijinal döner ve `translated=false`.
- **UI:** kartta küçük **"çevrildi"** rozeti; üzerine gelince / dokununca orijinal başlık; kaynak
  linki her zaman orijinal makaleye. Tema-uyumlu, mobilde ≥36 px dokunma alanı (mobil test paketi
  kapsar).
- **Diğer yüzeyler:** bülten/uyarı e-postaları abonenin `language`ına göre başlık/özet; RSS
  `?lang=`; WS canlı akış istemci diline göre; Chroma metadata'sına iki dilli başlık.
- **Hata modu:** kota/parse hatasında yalnız çeviri düşer, haber orijinal dilde görünür; oran
  `nexstream_translation_missing_total` ile izlenir.

### 4.5 Çapraz dilli arama ve RAG (S5)
- **Embedding metni** = orijinal + çeviri (`"{title}. {summary} || {title_alt}. {summary_alt}"`);
  çok dilli model zaten dil-aşırı, ama iki dilli metin eşleşme skorunu yükseltir (yeniden
  indeksleme S6'nın parçası).
- **Anahtar kelime:** `keyword_search` başlık/özet/içerik **ve** `*_i18n` alanlarında arar.
- **Sorgu çevirisi:** `GroqQueryExpander` mevcut çağrısına "sorgunun karşı dildeki karşılığı" alanı
  ekler (120b havuzu, sorgu başına 1 çağrı, önbellekli); semantik + anahtar kelime iki sorgu
  biçimiyle çalışır, en iyi skor alınır.
- **RAG eşiği:** çapraz dil eşleşmesi için dil-aşırı ceza yok; kanıt paketi kullanıcı dilindeki
  metni (`title_i18n[lang]`) LLM'e verir; cevap dili arayüz dili.
- Ölçüt testi: "iklim değişikliği ne durumda" → The Verge/TechCrunch iklim haberleri kanıt
  paketinde; "climate change" → TR iklim haberleri.

### 4.6 Eski veri (S6)
- **Lazy:** kullanıcı bir kartı görüntülediğinde (feed sayfasındaki eksik çeviriler tek toplu
  çağrıyla, önbelleğe yazılır) — yalnız kimliği doğrulanmış/insan oturumunda tetiklenir (bot
  trafiği kota yakmasın).
- **Arka plan:** worker boşta ve kota %70'in altındaysa son 7 günden geriye doğru, tek çağrıda
  çeviri + konu yeniden sınıflandırma + `shelf_life`. Günlük üst sınır (ör. 150 haber).
- Chroma yeniden indekslemesi aynı işin sonunda.

## 5. Kapasite modeli

| | Şimdi | Sonra (tahmin) |
|---|---|---|
| Çağrı başı token | ~530 (320+210) | ~570 (prompt +30 konu/raf ömrü, completion +~70 çeviri, −~30 etiket) |
| Günlük haber (hedef) | 1044 | 900-950 (tavanlar) |
| Günlük token | 551K | ~530K (+%0 net) |
| Nötr-yedek | 40 (%3,8) | ≤ %5 hedef |
Varsayım *ölçülecek*: S4 sonrası gerçek `usage` alanıyla 2-3 gün izlenir; tavanlar env ile ayarlanır.
Sorgu çevirisi (S5) 120b havuzundadır, haber hattını etkilemez. Gerçek bir 20 haberlik örnekle
prompt doğrulaması (JSON geçerliliği + çeviri kalitesi + token) S4'ün ilk adımıdır.

## 6. Test stratejisi
- Her dilim TDD (mock'lu); ağ yok. Yeni: prompt/ayrıştırıcı sözleşme testleri, tavan/tazelik alım
  testleri, `expires_at` filtre testleri, aciliyet sezgisi, `lang` API testleri, çapraz dil
  sorgu çevirisi (mock expander), frontend `node --test` (dil seçimi yardımcıları) ve Playwright
  mobil paketine rozet + çevrilmiş kart senaryosu.
- Gerçek Groq ile yalnız küçük doğrulama betikleri (≈20 çağrı ≈ 10K token).
- Prod duman testleri (deploy sonrası): "altın fiyatı", "iklim değişikliği", TR/EN kart dili,
  `RestartCount`, konu dağılımı sorgusu.

## 7. Riskler ve açık noktalar
- **Çeviri kalitesi/telif:** başlık çevirisi türev içeriktir; orijinal başlık + kaynak linki her
  zaman görünür (24 Ağu telif değerlendirmesinin "kaynak atfı" şartı korunur).
- **Kota:** ölçüm varsayımı yanlışsa tavanlar düşürülür; yedek olarak çeviri `medium/long`
  haberlerle sınırlanabilir (`short` raf ömürlü haber çevrilmez).
- **`Other` yüksek kalabilir:** S1 sonrası dağılım ölçülür, konu ipuçları güncellenir.
- **Sabit dil listesi:** yalnız TR/EN; yeni dil = `_STRINGS` benzeri sözlük bloğu, kod dalı yok.
- **Migration:** `news_articles` ALTER (JSON ×2, `source_lang`, `expires_at`), prod'da elle
  çalıştırılır (`migrations/` deseni); geri alma: sütunlar yoksayılır, API orijinale düşer.
- **Kapsam dışı:** tam makale metni (#18), yerel MT modeli (Hetzner sonrası, port hazır),
  Reddit/NPR, tema/UI yenilemesi (yol haritası C ayrı tasarım).

## 8. Bu tasarımın kullanıcıya bıraktığı kararlar
Onaylananlar: 4 yeni konu, öneri kaynak paketi, "analiz çağrısında çeviri + eskiler lazy",
"çevrildi" rozeti + orijinal başlık, tazelik önceliği. **İncelemede özellikle bak:** §4.3 raf
ömrü yaklaşımı (LLM'e yeni alan + kural tabanlı geçmiş), §4.2 başlangıç tavanları, §4.4 API
sözleşmesi (`lang`, `translated`, `original_*`).
