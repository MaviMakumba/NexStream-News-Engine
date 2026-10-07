# RAG — soru anında tam makale metni (design)

**Tarih:** 7 Ekim 2026 · **Durum:** kullanıcı onaylı tasarım (A seçeneği), plan bekliyor

## Amaç

"Soru Sor" (RAG, roadmap #13) cevabı bugün yalnızca başlık + RSS teaser'ına
(`content[:500]`, ~30-80 kelime) dayanıyor. Canlı bulgu (7 Eki 2026): son dakika
sakatlık haberinde kulüp doktorunun açıklaması makale gövdesinde vardı, başlıkta
ve teaser'da yoktu; "ne zaman sahaya döner?" sorusuna "bilmiyorum" döndü.

Hedef: kanıt paketindeki en iyi haberlerin **tam metnini soru anında** çekip,
soruyla en alakalı pasajları LLM'e vermek — token maliyetini sınırlı tutarak,
tam metni kalıcı saklamadan.

## Kapsam

**İçinde:** soru anında çekme, pasaj seçimi, kısa TTL'li cache, fail-open
davranış, SSRF/boyut/zaman korumaları, metrikler.

**Dışında (YAGNI):** DB'de tam metin saklama, ingest anında çekme (roadmap #18'in
ayrı kararı), JS render gerektiren siteler (Playwright), kaynak başına özel
çıkarıcı, soru-cevap arayüzünde yeni gösterge.

## Kararlar (kullanıcıyla netleşenler)

1. **Tetikleme (A):** her soruda, kanıt paketindeki en iyi **2** haber için.
   "Önce teaser'la dene, olmazsa ikinci çağrı" (B) reddedildi: gecikme ve
   LLM çağrısı iki katına çıkıyor, teaser'la yanlış cevap riski var.
2. **Haber bulma yeni algoritma gerektirmez:** `answer_question` zaten
   `hybrid_search` + özel isim doğrulamasıyla kanıt paketini kuruyor; çekme bu
   paket oluştuktan SONRA çalışır. Habere özel modda hedef haber her zaman
   paketin başındadır (hep zenginleşir).
3. **Haber yaşı önemsiz:** URL canlıysa 3 saatlik de 3 günlük de çekilir.
4. **Telif:** tam metin DB'ye YAZILMAZ (CLAUDE.md, telif değerlendirmesi:
   madde 18 kararına sadakat). Yalnız kısa TTL'li cache'te yaşar. API yanıt
   şeması değişmez (kaynak adı + başlık + link).

## Birimler

| Birim | Katman | Sorumluluk | Bağımlılık |
|---|---|---|---|
| `ArticleTextPort.fetch(url) -> str \| None` | `domain/ports/article_text_port.py` | URL'den temiz makale metni sözleşmesi; başarısızlıkta `None`, ASLA fırlatmaz | — |
| `HttpArticleTextFetcher` | `adapters/scrapers/article_text_fetcher.py` | httpx ile çeker (`BaseRssScraper._USER_AGENT` yeniden kullanılır), bs4+lxml ile gövde çıkarır; SSRF/boyut/içerik-türü korumaları | httpx, bs4, lxml (zaten `requirements.txt`'te) |
| `CachingArticleTextFetcher` | `adapters/scrapers/` (decorator) | `CachePort` ile başarı 1 saat, başarısızlık 5 dk cache | `CachePort` |
| `select_passages(text, question_vec, ...)` | `domain/services/passage_selection.py` | Saf fonksiyon: paragraflara böl, soruyla kosinüs benzerliği, token bütçesi içinde en iyi N paragraf (özgün sırada) | `EmbeddingPort` (enjekte) |
| `EvidenceEnricher` | `application/services/evidence_enricher.py` | En iyi 2 habere paralel çekme + pasaj seçimi, toplam zaman bütçesi, `content`'i değiştirir | yukarıdakiler |

`news_service.py` zaten çok büyük: oraya mantık eklenmez, `answer_question`'a
yalnızca tek bir "zenginleştir" çağrısı girer (kanıt sözlüklerinin oluşturulduğu
yerde, `content[:500]` yerine).

`src/infrastructure/*` hiçbir `src/adapters/*` import etmez (CLAUDE.md). Yeni
modüllerin import'ları `requirements-light.txt` (scheduler) etkilenmeyecek
şekilde yalnızca app/worker image'ında kalır; `test_embedder_image_closure.py`
ve `test_logger_no_web_deps.py` yeşil kalmalı.

## Veri akışı

Soru → retrieval + özel isim doğrulaması (DEĞİŞMEZ) → kanıt paketi →
en iyi 2 haber (hedef varsa o dahil) → URL için cache'e bak → yoksa çek →
paragrafları `embed_batch` ile soruya göre sırala → bütçe içinde seçilen
pasajlar o haberin `content` alanı olur → `qa_port.answer(...)`.

Pasaj seçimi `embedder` servisine ek bir HTTP çağrısı yapar (soru + paragraflar
tek `embed_batch`); embedder düşükse o haber teaser'a düşer.

## Hata ve güvenlik

- **Fail-open her adımda:** paywall/403/timeout/boş metin/embedder hatası →
  o haber eski `content[:500]` ile devam eder; kullanıcı hata görmez.
- **Zaman bütçesi:** haber başına 4 sn, toplam 6 sn; aşılırsa iptal.
- **SSRF:** yalnız http/https; DNS çözümü + HER yönlendirme sonrası IP kontrolü
  (özel/loopback/link-local/reserved reddedilir); en çok 3 yönlendirme.
- **Boyut:** gövde en fazla ~1,5 MB okunur (akış kesilir); `text/html`
  dışındaki içerik türleri atılır.
- **Çıkarıcı:** `<article>` / paragraf yoğunluğu; script/style/nav/aside/form
  atılır; çok kısa sonuç (< ~200 karakter) "çekilemedi" sayılır.

## Token ve kota

Hedef: haber başına ~300-500 token, soru başına ek ≈1-1,5K. Tavanlar
`settings`'te: `rag_fetch_top_n=2`, `rag_passage_token_budget=450` (haber
başına), `rag_fetch_timeout_seconds=4`, `rag_fetch_total_timeout_seconds=6`,
`rag_fetch_cache_ttl_seconds=3600`, `rag_fetch_enabled=True` (kapatma anahtarı).
Gerekçe: 120b'de RAG payı ~50K token/gün (worker taşma bütçesi 150K), ham tam
metin günde ~10 soruya mal olurdu.

Metrikler (`nexstream_` önekli): `article_fetch_total{result=hit|fetched|failed|blocked|too_short}`,
`article_fetch_seconds` histogramı. Hangi kaynağın bloklandığı Grafana'dan
görülür.

## Test (TDD, hepsi mock'lu — ağ sınırı conftest'te kapalı)

- Çıkarıcı: kaynak başına küçük HTML fixture'ları (gerçek sayfa kopyası değil,
  yapısal özet); script/nav gürültüsü; çok kısa sonuç; yanlış içerik türü.
- SSRF: özel IP, loopback, yönlendirmeyle özel IP'ye kaçış, `file://`.
- `select_passages`: deterministik sahte embedder; bütçe sınırı; özgün sıra.
- Cache decorator: hit/miss, başarısızlık TTL'i.
- `EvidenceEnricher`: kısmi başarısızlık, toplam zaman aşımı, paralellik,
  `rag_fetch_enabled=False`.
- `answer_question` entegrasyonu: fetch hata verince cevap eskisi gibi üretilir.
- **Regresyon (sakatlık örneği):** teaser'da olmayan, makale gövdesinde geçen
  bilgi LLM'e giden kanıta ulaşıyor mu.

## Dağıtım ve doğrulama

Deploy akışı değişmez (CI imajları, `deploy_images.sh`). Deploy sonrası:
`nexstream_article_fetch_total` sonuç dağılımı, kaynak bazlı `blocked`/`failed`
oranı, 120b token/saat (RAG payı), `RestartCount`/OOM kontrolü. Bloklanan
kaynaklar için ayrı iş (kaynak bazlı kural) metriğe bakılarak açılır; ilk
sürümde eklenmez.

## Açık risk

Bazı kaynaklar (AA gibi) WAF ile bot imzasını reddedebilir; fail-open olduğu
için kullanıcı etkilenmez ama kazanç o kaynaklarda sıfırdır. Metrik bunu
görünür kılar.
