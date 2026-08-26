# RAG Tabanlı Soru-Cevap ("Kanıta Dayalı Haber Asistanı") — Tasarım Spec'i

**Tarih:** 26 Ağustos 2026
**Roadmap maddesi:** #13
**Durum:** Onaylandı, implementasyon planına geçilecek

## Amaç

NexStream RAG, haber arama motorunun üzerine kurulmuş bir "arama sonuçlarını
paragrafa çeviren" chatbot **DEĞİLDİR**. Amaç: NexStream'in kendi haber
korpusundan ve kendi ürettiği intelligence metadata'sından (sentiment, topic,
quality_score, credibility_score, corroboration_count) kanıt toplayan, bu
kanıtın sorunun tamamını mı kısmen mi hiç mi karşıladığını **backend'de
deterministik olarak** belirleyen ve yalnızca **tek bir** LLM çağrısıyla bu
kanıtlara dayanarak sentez üreten bir "evidence-grounded" asistan kurmak.

**"Bu konuda kanıt/haber yok" bir başarısızlık durumu değil, ürünün zaten
merkezinde olan doğrulama/güvenilirlik felsefesinin (corroboration/credibility
skorlaması, v1.8) doğal bir uzantısıdır** — küçük/küratize bir korpusta
(17 kaynak, ~90 gün retention) "hiç kaynak bahsetmiyor" gerçek bir sinyaldir,
gizlenecek bir eksiklik değil.

İki giriş noktası olacak, aynı backend mekanizmasını paylaşarak:
1. **Genel sohbet** — yeni bir üst-seviye sayfa (`/dashboard/ask`), tüm
   korpusta serbest soru-cevap.
2. **Habere özel sohbet** — `NewsCard`'dan başlatılan, o habere (+ story
   cluster'ına) bağlamlı bir soru-cevap; genel sohbetten **tamamen ayrı**
   bir oturum olarak.

## Kapsan dışı (YAGNI — V1'de bilinçli olarak YAPILMAYACAKLAR)

- **Ayrı bir "Query Understanding" LLM çağrısı / niyet sınıflandırması YOK.**
  Kanıt yeterliliği kararı LLM'e "bu ne tür bir soru" diye sorularak değil,
  retrieval skorlarından + kaynak sayısından **kodda** hesaplanır.
- **Soru başına 1'den fazla Groq çağrısı YOK.** En fazla 1 (kanıt yoksa 0).
  Groq free tier kotası paylaşılan bir kaynak (haber analiz hattı + query
  expansion ile), bkz. CLAUDE.md BİLİNEN NOTLAR — yeni bir tüketici bu kotayı
  hızlandırıp tüketmemeli.
- **Web'den dış haber araması YOK.** NexStream'in kimliği "internetteki her
  şeyi bulan AI" değil, "kendi bildiği 17 kaynak arasında bağlantı kuran
  asistan"dır. Mimari buna kapalı değil (bkz. Açık Noktalar) ama V1'de
  inşa edilmiyor.
- **Ayrı bir `EvidenceRetrievalPort` soyutlaması YOK.** Tek bir retrieval
  yolu (`hybrid_search` + `get_story_cluster`) yeterli; tek implementasyonu
  olan bir soyutlama katmanı şimdiden eklemek gereksiz dolaylılık.
- **Kalıcı sohbet geçmişi (DB tablosu) YOK.** Sohbet geçmişi sadece
  tarayıcıda (React state), sayfa yenilenince/kapanınca kaybolur.
- **LLM kendi kaynağını/URL'sini ÜRETMEZ.** Model sadece numaralandırılmış
  kaynaklara referans verir; gerçek `url`/`source` backend'in elindeki
  retrieval sonucundan gelir.
- **Anonim erişim YOK.** Giriş zorunlu + Pro+ tier gating (`get_related`'daki
  aynı desen) — her soru bir Groq çağrısı demek, paylaşılan kotayı anonim
  trafiğe açmak riskli.
- **İkinci bir keyword listesi/uyarı mekanizması YOK.** "Bu konuda haber
  çıkınca haberdar et" aksiyonu, zaten var olan `POST /subscriptions/`
  (instant frequency, Pro+ gated) akışına yönlendirir — yeni bir backend
  mekanizması icat edilmiyor.

## Mimari & Bileşenler

Hexagonal desene uyularak:

- **Domain port:** `src/domain/ports/question_answering_port.py` →
  `QuestionAnsweringPort` (ABC). `AnalysisPort`'a metot EKLEMİYORUZ — proje
  zaten aynı gerekçeyle `QueryExpansionPort`'u `AnalysisPort`'tan ayrı tutmuş
  (ikisi de Groq kullanır ama farklı sorumluluklar, ISP ihlali riski).

  ```python
  class QuestionAnsweringError(Exception):
      """Groq çağrısı tamamen başarısız olduğunda fırlatılır. AnalysisPort'un
      aksine SESSİZ NÖTR FALLBACK YOK — bir soruya 'kibarca uydurulmuş' bir
      cevap vermek, açık bir hata vermekten daha kötü (kullanıcı yanlış
      bilgiye güvenebilir)."""

  class QuestionAnsweringPort(ABC):
      @abstractmethod
      def answer(
          self,
          question: str,
          sources: list[dict],          # bkz. "Kanıt paketi" bölümü
          history: list[dict],          # [{"role": "user"|"assistant", "content": str}, ...]
          corroboration_level: str,     # "single_source" | "multi_source"
      ) -> dict:
          """Dönüş: {"coverage": "full"|"partial"|"none", "answer": str,
          "used_sources": list[int]}. Başarısızlıkta QuestionAnsweringError
          fırlatır (fail-open DEĞİL, fail-loud — bkz. Kapsam dışı)."""
  ```

- **Adapter:** `src/adapters/analysis/groq_question_answerer.py` →
  `GroqQuestionAnswerer(QuestionAnsweringPort)` — `GroqAnalyzer`'daki
  rate-limit/retry/timeout HTTP deseninin (429 → Retry-After bekle, 5 deneme)
  birebir aynısı, ayrı bir prompt/parse mantığıyla.
- **Paylaşılan prompt/parse yardımcıları:** `src/adapters/analysis/rag_common.py`
  (`common.py`'nin Q&A karşılığı) → `build_rag_prompt(...)`,
  `parse_rag_json(content) -> dict`. `parse_rag_json` `common.py::parse_analysis_json`
  ile aynı disiplinde: `coverage` sabit 3 değerden biri değilse `"none"`a
  düşürülür (VALID_TOPICS deseni), `used_sources` liste değilse veya eleman
  tipi int değilse boş listeye düşürülür (malformed-result guard — bkz.
  CLAUDE.md "arama ilişkisel genişletme" dersi, aynı defect class).
- **Factory:** `src/adapters/analysis/factory.py::build_question_answerer() ->
  QuestionAnsweringPort` — şimdilik tek implementasyon (`GroqQuestionAnswerer`),
  `build_analyzer()`'daki gibi fallback zinciri YOK (HuggingFace'in Q&A
  karşılığı yok, YAGNI).
- **`NewsService`** yeni opsiyonel bağımlılık alır: `qa_port:
  Optional["QuestionAnsweringPort"] = None` — mevcut `subscriber_repository`/
  `email_port`/`query_expander` None-safe deseniyle aynı.
- **Yeni orkestrasyon metodu:** `NewsService.answer_question(question: str,
  article_id: Optional[int] = None, history: Optional[list[dict]] = None) -> dict`
  — bkz. "Veri Akışı" bölümü, mevcut `get_related`/`get_story_cluster` gibi
  `self.repository`/`self.search_repository`'yi zaten olduğu gibi kullanır,
  YENİ bir repository metodu gerekmez (`get_article_by_id`,
  `get_articles_by_ids` zaten var ve `quality_score`/`credibility_score`/
  `corroboration_count` dahil tam `Article` satırını döner).
- **Endpoint:** `POST /news/ask` (`news_router.py`, `get_related` ile aynı
  dosya/stil) — Pro+ gated + `check_tier_limit` + `10/minute` rate limit
  (Groq maliyeti nedeniyle `get_related`'ın 60/minute'undan daha sıkı).
- **Pydantic şemaları** (`news_schema.py`'e eklenir):
  ```python
  class AskMessage(BaseModel):
      role: str   # "user" | "assistant"
      content: str

  class AskRequest(BaseModel):
      question: str
      article_id: Optional[int] = None
      history: list[AskMessage] = []

  class RagSource(BaseModel):
      index: int
      title: str
      source: str
      url: str

  class RagAnswerResponse(BaseModel):
      answer: str
      coverage: str            # "full" | "partial" | "none"
      corroboration_level: str # "single_source" | "multi_source" | "none"
      sources: list[RagSource]
      suggest_alert: bool      # coverage == "none" ve genel modda True
  ```
- **DI wiring:** `dependencies.py::get_news_service` — `qa_port=build_question_answerer()`
  eklenir (`query_expander` ile aynı satır deseni).
- **Frontend:**
  - Yeni sayfa `frontend/app/dashboard/ask/page.tsx` — Dashboard/Arama'nın
    yanına yeni bir nav öğesi ("Soru Sor" / "Ask", i18n sözlüğüne eklenir).
  - `NewsCard.tsx`'e mevcut ikon-chip sırasına (İlgili/Kaynaklar/Dinle/Kaydet)
    yeni bir "💬 Sor" butonu — tıklanınca panel AÇMAZ, `router.push(
    '/dashboard/ask?articleId=' + article.id)` ile sayfaya yönlendirir
    (kullanıcının kararı — "haber kartının yanına bir buton, basınca oraya
    yönlendirsin").
  - `frontend/lib/api.ts`'e `askQuestion(body: AskRequest): Promise<RagAnswerResponse>`.

## Kanıt Kapısı ve Kapsam Belirleme (tasarımın çekirdeği)

İki farklı soru, iki farklı yerde cevaplanır — bunları KARIŞTIRMAMAK
tasarımın en kritik kararı:

1. **"Kaç bağımsız kaynak bunu doğruluyor?"** → objektif, sayılabilir bir
   gerçek. **Kodda, Groq'a hiç sormadan** hesaplanır.
2. **"Bu içerik sorunun tamamını mı, bir kısmını mı, hiçbirini mi
   cevaplıyor?"** → anlamsal bir okuma işi, bir similarity skoruyla
   ÖNCEDEN kestirilemez ("alakalı" ≠ "cevaplıyor"). Bunun için AYRI bir
   LLM çağrısı YOK — zaten yapılacak TEK sentez çağrısının kendisi bu
   soruyu okuyup yapılandırılmış bir `coverage` alanıyla cevaplar.

### Adım 1 — Retrieval (mevcut, değişmiyor)

- Genel mod: `candidates = self.hybrid_search(question, n_results=8)`.
- Habere özel mod: `target = self.repository.get_article_by_id(article_id)`
  (yoksa 404) + `get_story_cluster(article_id)["sources"]` (aynı olayı
  anlatan diğer kaynaklar) — `target` HER ZAMAN listede olur (skor eşiğinden
  bağımsız, çünkü kullanıcı zaten O haberi soruyor).

### Adım 2 — Kanıt kapısı (deterministik, kod, ücretsiz)

```python
RETRIEVAL_THRESHOLD = 0.5  # implementasyon sırasında gerçek sorularla kalibre edilecek

passing = [c for c in candidates if c["score"] >= RETRIEVAL_THRESHOLD]
if article_id is not None:
    passing = [target_as_source] + passing  # target eşikten muaf

if not passing:
    return NO_EVIDENCE_RESPONSE  # Groq'a HİÇ gidilmez, kota harcanmaz
```

`NO_EVIDENCE_RESPONSE`: `coverage="none"`, dürüst şablon cevap ("Takip
ettiğim kaynaklarda bu konuda doğrulanabilir bir gelişme bulunmuyor."),
`sources=[]`, `suggest_alert=True` (sadece genel modda — habere özel modda
target zaten her zaman en az 1 kaynak olduğu için bu dal pratikte hiç
tetiklenmez).

### Adım 3 — Doğrulama seviyesi (deterministik, kod)

`passing` listesindeki FARKLI `source` (yayın organı) sayısı ≥ 2 ise
`corroboration_level = "multi_source"`, değilse `"single_source"`. Bu bir
GERÇEK olarak prompt'a verilir, tahmin ettirilmez.

### Adım 4 — Kanıt paketi zenginleştirme

`passing`'teki her adayın `id`'si ile `self.repository.get_articles_by_ids(...)`
çağrılır (zaten var olan metot) — tam `Article` satırı (`quality_score`,
`credibility_score`, `corroboration_count`, `sentiment_label`, `topic`,
`published_at`) elde edilir. Numaralandırılmış kanıt paketi oluşturulur:

```
[1] Başlık: "..." | Kaynak: Sözcü | Sentiment: Negative | Doğrulayan kaynak: 3 | Tarih: 2026-08-25
[2] Başlık: "..." | Kaynak: BBC Türkçe | Sentiment: Neutral | Doğrulayan kaynak: 1 | Tarih: 2026-08-24
```

### Adım 5 — TEK Groq çağrısı (durum-farkında prompt)

`self.qa_port.answer(question, sources=evidence_bundle, history=history,
corroboration_level=level)`. Prompt kuralları `corroboration_level`'e göre
hafifçe değişir (ör. `multi_source` ise "kaynaklar arasında hemfikirlik/
ayrılık varsa belirt" talimatı eklenir) ama **çağrı sayısı hep 1**.

Sabit kurallar (her durumda):
- SADECE verilen kanıtları kullan, verilmeyen hiçbir isim/rakam/detay uydurma.
- Kaynaklara SADECE `[1]`, `[2]` gibi numarayla referans ver, asla URL/kaynak
  adı üretme.
- `coverage` alanını dürüstçe doldur: soru TAM cevaplanıyorsa `"full"`,
  KISMEN (ör. "ne oldu" var ama "neden" yok) cevaplanıyorsa `"partial"`,
  kanıtlar soruyla hiç örtüşmüyorsa `"none"`.
- Aynı dilde cevap ver (soru TR ise TR, EN ise EN — mevcut analiz prompt'undaki
  bilingual kural).

### Adım 6 — Backend post-processing (LLM'e güvenme, doğrula)

```python
result = parse_rag_json(raw_content)  # coverage/used_sources/answer şemaya zorlanır

if result["coverage"] == "none":
    # Model 'answer' alanına ne yazmış olursa olsun GÖZ ARDI EDİLİR —
    # dürüst şablon + varsa "buna yakın" adaylar + suggest_alert
    return NO_EVIDENCE_STYLE_RESPONSE

result["used_sources"] = [i for i in result["used_sources"] if 1 <= i <= len(evidence_bundle)]  # clamp
return {
    "answer": result["answer"],
    "coverage": result["coverage"],       # "full" | "partial"
    "corroboration_level": level,
    "sources": [evidence_bundle[i-1] for i in result["used_sources"]],
    "suggest_alert": False,
}
```

Bu, kullanıcı tarafından işaret edilen beş-seviyeli merdiveni (NO_EVIDENCE /
WEAK / PARTIAL / SUFFICIENT / MULTI_SOURCE_EVIDENCE) hâlâ üretir — ama arka
planda ayrı bir sınıflandırıcı yerine **1 deterministik kapı + 1 sayım +
1 LLM çağrısının yapılandırılmış çıktısı** kombinasyonundan türer.

## Frontend Sohbet Oturumu Ayrımı

Kullanıcının kritik şartı: **genel sohbet ile habere özel sohbet birbirini
HİÇ etkilemesin.**

```typescript
type SessionId = "general" | `article:${number}`;

const sessionId: SessionId = articleIdParam
  ? `article:${articleIdParam}`
  : "general";

// Her sessionId için AYRI mesaj geçmişi — React state, Record<SessionId, Message[]>.
// Sayfa yenilenince/URL değişince (farklı bir habere tıklanınca) o session'ın
// geçmişi SIFIRDAN başlar — kalıcı saklama yok (bilinçli karar, bkz. Kapsam Dışı).
```

Bir karttan `/dashboard/ask?articleId=123`'e gidilir, sonra nav'dan "Soru
Sor"a tıklanırsa `general` session'a döner — `article:123` geçmişi
bozulmadan (state'te) durur ama görünmez, tekrar o karta tıklanınca geri gelir.

## "Bu konuda haber çıkınca haberdar et" (suggest_alert)

`coverage="none"` VE genel moddaysa, cevabın altında bir aksiyon butonu
gösterilir: **"🔔 Bu konuda haber çıkarsa bildir"**. Tıklanınca YENİ bir
backend mekanizması OLUŞTURULMAZ — kullanıcı `/account`'a, sorusundan
türetilmiş bir anahtar kelime ÖN-DOLDURULMUŞ olarak yönlendirilir (V1'de
en basit yol: `/account?prefillKeyword=<soru metni>` query param'ı, hesap
sayfasındaki mevcut abonelik formunu doldurur). Gerçek kayıt zaten var olan
`POST /subscriptions/` (`frequency="instant"`, Pro+ gated) akışından geçer.
**Bu aksiyon cevabın BAŞINDA değil SONUNDA, ikincil bir öneri olarak
görünür** — önce dürüst kanıt-durumu cevabı, sonra (varsa) aksiyon.

## Hata Yönetimi

- `GroqQuestionAnswerer.answer()` tüm denemeler başarısız olursa
  `QuestionAnsweringError` fırlatır (AnalysisPort'un aksine sessiz nötr
  fallback YOK — bkz. Amaç). `NewsService.answer_question` bunu yakalayıp
  yeniden fırlatır (ya da özel bir `{"error": "..."}" durumuna çevirir),
  router 503 döner: *"Şu an yanıt üretemiyorum, birazdan tekrar dene."*
  Bu, `NO_EVIDENCE` durumundan (200, dürüst "kanıt yok" cevabı) AÇIKÇA
  farklı bir HTTP/durum kodu ile ayrılır — kullanıcı ikisini karıştırmamalı.
- `parse_rag_json` malformed JSON/eksik alan durumunda `coverage="none"`a
  düşer (fail-safe, `common.py::parse_analysis_json`'daki topic-guard
  deseniyle aynı disiplin).
- `used_sources` şemaya uymuyorsa (aralık dışı index, yanlış tip) clamp
  edilir/boşa düşürülür — malformed-result guard, "arama ilişkisel
  genişletme" dersindeki AYNI defect class.
- `article_id` geçersizse (habere özel modda) 404.
- Free/anonim kullanıcı → 403 (`get_related`'daki aynı hata mesajı deseni).
- Rate limit aşımı → slowapi'nin standart 429'u.

## Test Planı

TDD, gerçek Groq/HTTP çağrısı yok (proje kuralı) — AMA bu özellik için ekstra
bir adım şart, çünkü asıl risk "kod çalışmıyor" değil "kod çalışıp saçma
cevap veriyor":

- **`GroqQuestionAnswerer`:** `GroqAnalyzer`'daki rate-limit/retry testlerinin
  aynısı (mock HTTP) + `parse_rag_json`'un coverage/used_sources guard'ları.
- **`NewsService.answer_question`:**
  - Retrieval boşsa (genel mod) → Groq HİÇ ÇAĞRILMADI + `NO_EVIDENCE` +
    `suggest_alert=True`.
  - Habere özel modda geçersiz `article_id` → 404/None.
  - `corroboration_level` doğru hesaplanıyor (tekil kaynak vs çoklu kaynak
    senaryoları, mock candidates ile).
  - `coverage="none"` dönerse backend modelin `answer`'ını GÖZ ARDI EDİP
    şablona düşüyor (mock qa_port farklı bir "answer" + coverage=none
    dönsün, test bunun kullanılmadığını doğrulasın).
  - `used_sources` aralık dışı index içerirse clamp ediliyor.
  - `qa_port=None` iken (opsiyonel bağımlılık) endpoint/servis anlamlı bir
    hata veriyor (diğer opsiyonel port'larla tutarlı davranış tanımlanacak).
- **`POST /news/ask`:** Free 403, Pro+ 200, rate limit 429, `QuestionAnsweringError`
  → 503.
- **Frontend:** `tsc --noEmit` + `npm run build`; session ayrımı (general vs
  article:N state'lerinin birbirini etkilemediği) için bir birim test
  (React state mantığı, browser API mock'u gerekmiyor).
- **⚠️ ZORUNLU canlı/manuel kalite doğrulaması (kod yeşil olsa bile
  ATLANMAZ — proje disiplini, bkz. Yahoo Finance sembolü dersi):**
  gerçek indexlenmiş haberlere karşı en az şu senaryolar elle denenip
  gözle değerlendirilecek, gerekirse `RETRIEVAL_THRESHOLD`/prompt ayarlanacak:
  1. Hiç haberi olmayan bir konu (ör. "Beşiktaş'ın sağ kanat transferi") →
     `NO_EVIDENCE` + `suggest_alert` bekleniyor.
  2. Tek kaynaklı, derin bir soru (ör. bir fiyat haberinin "nedeni") →
     `coverage="partial"` bekleniyor, model boşluğu DOLDURMAMALI.
  3. Çok kaynaklı, iyi kapsanan bir konu → `coverage="full"` +
     `corroboration_level="multi_source"` + kaynaklar arası tutarlılık/
     ayrılık doğru sentezlenmiş olmalı.
  4. Dolaylı-alakalı ama doğrudan olmayan bir soru (ör. "Fenerbahçe'nin
     yeni teknik direktörü kim" — sadece "arayış" haberleri varsa) →
     model ilişkili gelişmeleri CEVAP GİBİ SUNMAMALI, `partial`/`none`
     arasında dürüst kalmalı.
  5. Takip sorusu (multi-turn) — "peki ya İzmir'de?" gibi bir önceki
     bağlama referans veren bir soru, history doğru taşınıyor mu.

## Açık Noktalar / Sonraki Adım

- `RETRIEVAL_THRESHOLD` kesin değeri implementasyon sırasında gerçek
  sorularla kalibre edilecek (0.5 sadece başlangıç varsayımı).
- Mimari, ileride bir `ExternalNewsRetriever` ile web araması eklemeye
  KAPALI değil (yeni bir kanıt kaynağı `Adım 1`e eklenip aynı Adım 2-6
  değişmeden çalışabilir) ama V1'de bu port/implementasyon YAZILMIYOR.
- Tüm bölümler kullanıcı tarafından, çok turlu bir mimari tartışma
  sonrasında onaylandı. Sıradaki adım `superpowers:writing-plans` ile
  implementasyon planı yazmak.
