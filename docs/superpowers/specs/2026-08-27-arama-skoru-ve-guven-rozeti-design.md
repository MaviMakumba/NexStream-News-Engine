# Arama skoru yeniden tasarımı + görünür güven rozeti — Tasarım

**Tarih:** 27 Ağustos 2026
**Dal:** `main`'den yeni bir kısa ömürlü feature branch açılacak
**Durum:** Tasarım onaylandı, uygulama bekliyor

---

## Problem

İki ayrı ama ilişkili eksiklik:

**A) `hybrid_search`'ün skoru sorgunun ÖZEL İSMİNİ hiç doğrulamıyor.** Skor
`max(semantik_skor, keyword_skor) + double-hit bonus`, sonra recency ile
çarpılıyor — ne `quality_score`/`credibility_score` (ingest anında zaten
hesaplanan sinyaller) skora katılıyor, ne de semantik tarafın bulduğu bir
sonucun sorgudaki özel ismi GERÇEKTEN içerip içermediği kontrol ediliyor. Bu,
27 Ağu 2026'da RAG canlı QA'sında bulunan "7. bulgu"nun (CLAUDE.md YOL
HARİTASI madde 13) kök nedeni: "Beşiktaş maçı saati" sorusunda retrieval
doğru haberi buluyor (%59.4 skor) ama kanıt paketi "maç" kelimesini paylaşan
TAMAMEN ALAKASIZ (farklı spor dalı/takım) şablon içeriklerle de doluyor —
semantik benzerlik yüksek olsa da "Beşiktaş" kelimesi o makalelerde hiç
geçmiyor. 24 Ağu 2026'da corroboration/related/story-cluster'da aynı bug
sınıfı `_distinguishing_entity_keys` ile çözülmüştü ama o ingest-zamanı
entity-overlap'e dayanıyor, `hybrid_search`'e doğrudan uygulanamaz.

**B) Kullanıcıya hiçbir yerde makalenin güvenilirliği görünmüyor.**
`quality_score`/`credibility_score`/`corroboration_count` ingest anında
hesaplanıyor, RAG kanıt paketinde `corroboration_count` var ama kart
üzerinde hiçbir yerde bir "bu habere ne kadar güvenebilirim" sinyali yok.

**Bağlantılı ama AYRI bir proje:** "Beşiktaş maçı saat kaçta/hangi kanalda"
gibi sorular için (A) sadece DOĞRU haberi bulmayı sağlar — haberin İÇİNDEKİ
detay (saat, stadyum) hâlâ RSS teaser'ında yok, bu ayrı bir çalışma
(full-article-scraping, CLAUDE.md YOL HARİTASI madde 18) gerektirir; o proje
bu spec'ten SONRA, kaldığı yerden (kapsam: RAG-only/on-demand, cache:
Redis TTL — zaten karara bağlandı) ayrıca ele alınacak. "Hangi kanalda" tipi
sorular muhtemelen HİÇBİR düzeltmeyle çözülmeyecek — 27 Ağu 2026'da canlı bir
makale sayfası WebFetch ile test edildi, saat bilgisi tam makalede VARDI ama
kanal bilgisi YOKTU; bu proje kapsamına alınmadı.

---

## Çözüm Özeti

**A) Deterministik, LLM çağrısı gerektirmeyen bir "grounding + credibility"
çarpanı** `hybrid_search`'ün mevcut skoruna eklenir — sıfır ekstra
gecikme/maliyet, tamamen zaten elde mevcut veriyle. **B)** Var olan üç
sinyalden (`quality_score`/`credibility_score`/`corroboration_count`),
sorgudan bağımsız, **okuma anında** hesaplanan 0-100 bir kompozit "güven
skoru" — `NewsCard`'da her yerde (dashboard, arama, RAG) görünür bir rozet +
tıklama/hover'da bileşen dökümü.

---

## A) `hybrid_search` skor düzeltmesi

### `_distinguishing_query_terms(query: str) -> list[str]` (yeni, `news_service.py`)

Sorgunun ORİJİNAL (küçültülmemiş) halinden büyük harfle başlayan kelimeleri
çıkarır (`"Beşiktaş maçı saat kaçta"` → `["Beşiktaş"]`). Cümle başındaki
büyük harf yanlış-pozitif riski taşır (`"Dün ne oldu"` → `"Dün"` özel isim
değil) — bu yüzden sadece **cümle başı hariç** büyük harfle başlayan
kelimeler VEYA sorgu tek kelimeyse (cümle başı ayrımı anlamsız) tüm büyük
harfli kelimeler alınır. Soru parçacıkları (`_TR_QUESTION_STOPWORDS`) zaten
elenir (mevcut `_canonical_terms` deseniyle tutarlı).

### `_grounding_factor(distinguishing_terms: list[str], article_text: str) -> float` (yeni)

```python
if not distinguishing_terms:
    return 1.0  # sorguda özel isim yok, dokunma
text = _tr_lower(article_text)
if any(re.search(r"\b" + re.escape(_tr_lower(t)), text) for t in distinguishing_terms):
    return 1.0
return _GROUNDING_PENALTY  # = 0.3, modül sabiti
```

`_tr_lower` + `\b`-anchor: dotted-İ dersiyle (27 Ağu 2026 RAG düzeltmesi)
aynı desen — yeni bir substring/case bug'ı riske edilmez. **Sert filtre
DEĞİL, çarpımsal ceza** — fail-open felsefesiyle tutarlı: sorgunun özel ismi
hiçbir sonuçta geçmiyorsa (ör. gerçekten alakasız bir konu), en azından en
yüksek SEMANTİK skorlu sonuç yine de (düşük skorla) görünür, tamamen
kaybolmaz.

### Credibility fold-in

```python
cred = article.credibility_score if article.credibility_score is not None else 0.5
credibility_factor = 0.7 + 0.3 * cred
```

**`or 0.5` DEĞİL, açık `is not None` kontrolü** — `credibility_score` meşru
olarak `0.0` olabilir (düşük ama geçerli bir değer), Python'da `0.0 or 0.5`
yanlışlıkla `0.5`'e döner (falsy-zero bug'ı, `article.py`'deki `corroboration_
count` gibi sayısal alanlarla ÇALIŞIRKEN hep bu deseni kullan). Skor aralığı
zaten `[0, 1]` (bkz. `domain/scoring/credibility.py`) — `None` durumunda
(henüz hesaplanmamış eski satır) nötr `0.5` varsayılır, `0.7 + 0.3*0.5 =
0.85` — hafif bir belirsizlik cezası.

### Birleştirme

`hybrid_search`'teki mevcut satır:

```python
final = round(relevance * self._decay_factor(recency), 4)
```

şuna genişler:

```python
grounding = self._grounding_factor(distinguishing_terms, f"{data.get('title','')} {content_text}")
cred = article_credibility if article_credibility is not None else 0.5
credibility = 0.7 + 0.3 * cred
final = round(relevance * self._decay_factor(recency) * grounding * credibility, 4)
```

`distinguishing_terms` sorgu başına BİR KEZ hesaplanır (fonksiyon başında,
`relevance_terms` ile aynı yerde) — döngü içinde tekrar tekrar hesaplanmaz.
Hem semantik-kökenli hem keyword-kökenli sonuçlar için ortak uygulanır (ikisi
de aynı `combined` döngüsünden geçiyor). **Sadece `hybrid_search`'ü etkiler**
— `get_related`/`get_story_cluster` kapsam dışı (24 Ağu'da kendi
düzeltmelerini zaten aldılar, farklı bir mekanizma — entity-overlap —
kullanıyorlar).

**Regresyon riski yok:** `grounding`/`credibility` her ikisi de `≤ 1.0`
çarpan — önceden iyi sıralanan bir sonuç ASLA daha yükseğe çıkmaz, sadece
zayıf sinyalli sonuçlar geriye düşer.

---

## B) Görünür güven rozeti

### Backend — `domain/scoring/` içinde saf fonksiyon (yeni, `trust.py`)

```python
def compute_trust_score(quality_score: float, credibility_score: float, corroboration_count: int) -> int:
    """0-100 arası tam sayı. Girdi None ise 0.5/0.5/0 varsayılır (nötr)."""
    q = quality_score if quality_score is not None else 0.5
    c = credibility_score if credibility_score is not None else 0.5
    corr = min((corroboration_count or 0) / 3, 1.0)
    return round(100 * (0.35 * q + 0.45 * c + 0.20 * corr))
```

Diğer `domain/scoring/` fonksiyonları gibi **dış bağımlılık yok, saf Python**
— `quality.py`/`credibility.py` ile aynı felsefe. **Saklanmaz, her okumada
hesaplanır** — `corroboration_count` zamanla artabildiği için (yeni bir
kaynak aynı olayı doğrularsa) saklanan bir değer bayatlar; okuma-anı hesabı
her zaman güncel kalır ve migration gerektirmez.

### Şema (`NewsResponse`/`SearchResult`)

Yeni alan: `trust_score: int` — `NewsService`'in ilgili dönüşüm noktalarında
(`list_news`, `hybrid_search`, `get_story_cluster` kaynak listesi vb.)
`compute_trust_score(...)` çağrısıyla dolduruluyor. Mevcut `quality_score`/
`credibility_score` alanları KALDIRILMIYOR (geriye uyumluluk) — `trust_score`
onların üstüne inşa edilen bir ÖZET, ayrı bir alan.

### Frontend — `NewsCard`

- Sağ üstte küçük bir rozet (`.icon-chip` deseniyle tutarlı, mevcut ikon
  butonları gibi — bkz. CLAUDE.md "emoji glif rengi" dersi, çıplak sayı
  yerine konteynerli): `82` gibi bir sayı + ince bir renk ipucu (yüksek/orta/
  düşük için token-tabanlı renk, tema sabit renk KULLANILMAZ — CLAUDE.md
  "v1.10 tema" kuralı).
- Tıklama/hover'da küçük bir açılır panel: bileşen dökümü, `lib/i18n.ts`
  sözlüğünden (SOLID i18n kuralı — if/else dil dallanması YOK). Örnek TR
  metni: *"82/100 — %45 kaynak güvenilirliği, %35 içerik kalitesi, %20 çoklu
  kaynak doğrulaması."* Yüzdeler `compute_trust_score`'un ağırlıklarından
  (0.45/0.35/0.20) türetilir, hardcode edilmez.
- Rozet `NewsCard`'ın göründüğü HER yerde (dashboard, arama sonuçları, RAG
  kanıt kartları, story cluster) aynı bileşenle render edilir — tek
  implementasyon, tek doğruluk noktası.

---

## Test stratejisi

**A (`hybrid_search`):**
- `_distinguishing_query_terms`: cümle başı büyük harf hariç tutuluyor mu,
  tek kelimelik sorguda büyük harf yine de yakalanıyor mu, soru
  parçacıkları eleniyor mu.
- `_grounding_factor`: özel isim makalede geçiyorsa 1.0, geçmiyorsa
  `_GROUNDING_PENALTY`, sorguda özel isim yoksa 1.0.
- `hybrid_search` regresyon: **mevcut TÜM testler değişmeden geçmeli**
  (yeni çarpanlar `credibility_score`/`quality_score` None olan mevcut test
  fixture'larında nötr `0.85` credibility + `1.0` grounding (özel isim yoksa)
  vermeli, sayısal beklentileri bozmamalı — gerekirse mevcut testlerin
  beklenen skor sabitleri güncellenecek).
- Yeni entegrasyon testi: dünkü "maç" bug'ının aynısını simüle eden bir
  senaryo (yüksek semantik skorlu ama özel ismi içermeyen bir aday, düşük
  semantik skorlu ama özel ismi içeren bir aday) — ikincinin öne geçtiğini
  doğrula.

**B (güven skoru):**
- `compute_trust_score`: sınır değerler (hepsi 0, hepsi 1, `corroboration_count`
  3'ü aştığında tavanlanıyor mu, `None` girdilerde nötr varsayılan).
- Şema/serialization: `trust_score` alanının `NewsResponse`/`SearchResult`'ta
  gerçekten dolu geldiğini doğrula.
- Frontend: rozet + breakdown panelinin doğru yüzdeleri gösterdiği (snapshot
  değil, hesaplanan değerlerle) + TR/EN i18n anahtarlarının ikisinin de
  dolu olduğu.

---

## Kapsam Dışı (bu turda YAPILMAYACAK)

- Full-article-text scraping (RAG kanıt zenginleştirmesi) — ayrı, bu spec'ten
  SONRA ele alınacak proje (CLAUDE.md YOL HARİTASI madde 18).
- "Hangi kanalda yayınlanıyor" tipi sorular — kaynak verimizde bu bilgi hiç
  yok, ayrı bir TV-yayın-programı veri kaynağı gerektirir, kapsam dışı.
- `get_related`/`get_story_cluster`'ın skor mekanizmasına dokunmak — zaten
  24 Ağu 2026'da kendi düzeltmelerini aldılar.
- Embedding/cross-encoder tabanlı bir re-ranking modeli — VPS RAM'i dar,
  A1'in deterministik yaklaşımı yetmezse gelecekte ayrı bir tur olarak
  değerlendirilebilir.
