# Arama Skoru Yeniden Tasarımı + Görünür Güven Rozeti — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `hybrid_search`'ün skoruna deterministik bir "sorgu-varlık doğrulaması" +
"güvenilirlik" çarpanı ekle (dünkü "maç" retrieval bug'ını çözer), ve
`quality_score`/`credibility_score`/`corroboration_count`'tan okuma-anında
hesaplanan 0-100'lük görünür bir "güven skoru" rozetini `NewsCard`'a ekle.

**Architecture:** Saf domain fonksiyonu (`compute_trust_score`, `domain/scoring/`)
+ `Article`'a bir `trust_score` property'si (böylece `NewsResponse` hiç ek kod
olmadan `from_attributes=True` ile otomatik alır) + `hybrid_search`/
`get_story_cluster`'da candidate id'ler için tek seferlik `Article` nesnesi
fetch'i (mevcut `get_articles_by_ids` deseni, N+1 değil) + frontend'de mevcut
`.badge` deseninin genişletilmesi (yeni bileşen/state YOK — hover `title=`
attribute'u, `corroborationText`'in aynı deseni).

**Tech Stack:** Python (FastAPI/Pydantic backend, pytest), TypeScript/React
(Next.js frontend, tip kontrolü `npm run build` ile).

**Spec:** `docs/superpowers/specs/2026-08-27-arama-skoru-ve-guven-rozeti-design.md`

## Global Constraints

- Regresyon riski YOK kuralı: yeni çarpanlar (`grounding_factor`,
  `credibility_factor`) her ikisi de `≤ 1.0` — önceden iyi sıralanan bir sonuç
  ASLA daha yükseğe çıkmayacak, sadece zayıf sinyaller geriye düşecek.
- `credibility_score`/`quality_score` `None` kontrolü HER YERDE `is not None`
  ile yapılır, `or 0.5`/`or 0.0` KULLANILMAZ (falsy-zero bug'ı — `0.0` meşru
  bir değerdir, `or` onu yanlışlıkla varsayılana çevirir).
- `_lower_tr_safe` (news_service.py'de zaten var, `subscriber_matching._tr_lower`
  ile KARIŞTIRILMASIN) + `\b`-anchor deseni her yeni literal-metin eşleşmesinde
  kullanılır — dotted-İ dersi.
- DB migration YOK — hiçbir yeni sütun/tablo eklenmiyor, `trust_score` her
  zaman okuma anında hesaplanan bir türetilmiş değer.
- Mevcut TÜM testler (837) değişmeden geçmeli — `hybrid_search`/
  `get_story_cluster` testlerinde beklenen sayısal skor sabitleri, yeni
  çarpanların nötr değerlerini (grounding=1.0 sorguda özel isim yoksa,
  credibility=0.85 `credibility_score=None` iken) yansıtacak şekilde
  güncellenmeli — davranış aynı kalmalı, sadece formül genişliyor.

---

### Task 1: `compute_trust_score` — saf domain fonksiyonu

**Files:**
- Create: `src/domain/scoring/trust.py`
- Test: `tests/domain/test_trust.py`

**Interfaces:**
- Produces: `compute_trust_score(quality_score: Optional[float], credibility_score: Optional[float], corroboration_count: int) -> int`

- [ ] **Step 1: Write the failing test**

```python
# tests/domain/test_trust.py
from src.domain.scoring.trust import compute_trust_score


def test_all_zero_scores_zero():
    assert compute_trust_score(0.0, 0.0, 0) == 0


def test_all_max_scores_hundred():
    assert compute_trust_score(1.0, 1.0, 10) == 100


def test_weights_sum_correctly():
    # quality=1.0 (%35) + credibility=0.0 (%0) + corroboration=0 (%0) = 35
    assert compute_trust_score(1.0, 0.0, 0) == 35


def test_corroboration_caps_at_three():
    # corroboration_count=3 ve 10, İKİSİ de tam %20 katkı vermeli (tavanlı)
    assert compute_trust_score(0.0, 0.0, 3) == compute_trust_score(0.0, 0.0, 10) == 20


def test_none_quality_and_credibility_use_neutral_default():
    # None -> 0.5 varsayılan, corroboration=0 -> 100*(0.35*0.5 + 0.45*0.5) = 40
    assert compute_trust_score(None, None, 0) == 40


def test_zero_is_not_treated_as_none():
    # credibility_score=0.0 GERÇEK bir değer, 0.5'e "or" ile geri düşmemeli
    low = compute_trust_score(0.5, 0.0, 0)
    neutral = compute_trust_score(0.5, None, 0)
    assert low < neutral


def test_result_is_always_int():
    result = compute_trust_score(0.73, 0.61, 2)
    assert isinstance(result, int)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `venv\Scripts\python.exe -m pytest tests/domain/test_trust.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'src.domain.scoring.trust'`

- [ ] **Step 3: Write minimal implementation**

```python
# src/domain/scoring/trust.py
"""Görünür "güven skoru" — quality/credibility/corroboration'ı tek bir 0-100
sayıya birleştiren saf hesap, dış bağımlılık yok (bkz. quality.py/credibility.py
ile aynı felsefe). SAKLANMAZ — her okumada hesaplanır, çünkü corroboration_count
zamanla artabilir (yeni bir kaynak aynı olayı doğrularsa) ve saklanan bir değer
bu durumda bayatlar.
"""
from typing import Optional

_QUALITY_WEIGHT = 0.35
_CREDIBILITY_WEIGHT = 0.45
_CORROBORATION_WEIGHT = 0.20
_CORROBORATION_FULL_AT = 3  # bu sayıda doğrulayan kaynaktan sonra tam puan


def compute_trust_score(
    quality_score: Optional[float],
    credibility_score: Optional[float],
    corroboration_count: int,
) -> int:
    # `or 0.5` DEĞİL — 0.0 meşru bir değer, is not None kontrolü şart.
    q = quality_score if quality_score is not None else 0.5
    c = credibility_score if credibility_score is not None else 0.5
    corr = min((corroboration_count or 0) / _CORROBORATION_FULL_AT, 1.0)
    return round(100 * (_QUALITY_WEIGHT * q + _CREDIBILITY_WEIGHT * c + _CORROBORATION_WEIGHT * corr))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `venv\Scripts\python.exe -m pytest tests/domain/test_trust.py -v`
Expected: 7 passed

- [ ] **Step 5: Commit**

```bash
git add src/domain/scoring/trust.py tests/domain/test_trust.py
git commit -m "feat: compute_trust_score saf domain fonksiyonu"
```

---

### Task 2: `Article.trust_score` property + `NewsResponse` şeması

**Files:**
- Modify: `src/domain/models/article.py`
- Modify: `src/domain/schemas/news_schema.py`
- Test: `tests/domain/test_article.py`

**Interfaces:**
- Consumes: `compute_trust_score` (Task 1)
- Produces: `Article.trust_score` (property, int) — `NewsResponse.trust_score:
  int` bunu `from_attributes=True` sayesinde OTOMATİK okur, router değişikliği
  gerekmez.

- [ ] **Step 1: Write the failing test**

```python
# tests/domain/test_article.py — dosyanın sonuna ekle
def test_article_trust_score_property():
    article = Article(
        title="T", source="BBC", url="u", content="c",
        quality_score=1.0, credibility_score=1.0, corroboration_count=10,
    )
    assert article.trust_score == 100


def test_article_trust_score_defaults_when_unscored():
    article = Article(title="T", source="BBC", url="u", content="c")
    assert article.trust_score == 40  # None/None/0 -> nötr varsayılanlar
```

- [ ] **Step 2: Run test to verify it fails**

Run: `venv\Scripts\python.exe -m pytest tests/domain/test_article.py -v -k trust_score`
Expected: FAIL — `AttributeError: 'Article' object has no attribute 'trust_score'`

- [ ] **Step 3: Write minimal implementation**

`src/domain/models/article.py` — dosyanın en üstüne import ekle, dataclass'ın
sonuna property ekle:

```python
from src.domain.scoring.trust import compute_trust_score
```

```python
@dataclass
class Article:
    # ... mevcut alanlar DEĞİŞMEDEN kalır ...
    id: Optional[int] = None

    @property
    def trust_score(self) -> int:
        return compute_trust_score(self.quality_score, self.credibility_score, self.corroboration_count)
```

`src/domain/schemas/news_schema.py` — `NewsResponse`'a yeni alan (mevcut
`corroboration_count: int = 0` satırından hemen sonra):

```python
class NewsResponse(BaseModel):
    # ... mevcut alanlar ...
    corroboration_count: int = 0
    trust_score: int = 0

    model_config = {"from_attributes": True}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `venv\Scripts\python.exe -m pytest tests/domain/test_article.py tests/adapters/test_news_repository.py -v`
Expected: tüm testler PASS (ORM/repository'ye dokunulmadı, sadece dataclass'a
salt-okunur bir property eklendi — geriye dönük uyumlu)

- [ ] **Step 5: Commit**

```bash
git add src/domain/models/article.py src/domain/schemas/news_schema.py tests/domain/test_article.py
git commit -m "feat: Article.trust_score property + NewsResponse alanı"
```

---

### Task 3: `_distinguishing_query_terms` + `_grounding_factor` — `NewsService` yardımcıları

**Files:**
- Modify: `src/application/services/news_service.py`
- Test: `tests/application/test_news_service.py`

**Interfaces:**
- Produces:
  - `NewsService._distinguishing_query_terms(query: str) -> List[str]` (staticmethod)
  - `NewsService._grounding_factor(distinguishing_terms: List[str], article: Article) -> float` (staticmethod)
- Consumes: `NewsService._lower_tr_safe` (mevcut, satır ~384)

- [ ] **Step 1: Write the failing test**

```python
# tests/application/test_news_service.py — "hybrid_search" test bloğunun
# başına, mevcut import'ların altına ekle (dosyanın üstünde zaten
# `from src.domain.models.article import Article` var, tekrar import gerekmez)

def test_distinguishing_query_terms_extracts_capitalized_first_word():
    # Dünkü canlı bug'ın TAM senaryosu: sorgu konu-önce yazılıyor, özel isim
    # genelde İLK kelime — cümle-başı hariç tutulsaydı bu senaryo kaçırılırdı.
    assert NewsService._distinguishing_query_terms("Beşiktaş maçı saat kaçta") == ["Beşiktaş"]


def test_distinguishing_query_terms_single_word_query_still_checked():
    assert NewsService._distinguishing_query_terms("Beşiktaş") == ["Beşiktaş"]


def test_distinguishing_query_terms_strips_trailing_punctuation():
    assert NewsService._distinguishing_query_terms("bu akşam Beşiktaş? maçı var mı") == ["Beşiktaş"]


def test_distinguishing_query_terms_empty_for_all_lowercase_query():
    assert NewsService._distinguishing_query_terms("maç saat kaçta") == []


def test_distinguishing_query_terms_multiple_capitalized_words():
    assert NewsService._distinguishing_query_terms("Beşiktaş Zalgiris maçı") == ["Beşiktaş", "Zalgiris"]


def test_grounding_factor_neutral_when_no_distinguishing_terms():
    article = Article(title="Herhangi bir haber", source="BBC", url="u", content="içerik")
    assert NewsService._grounding_factor([], article) == 1.0


def test_grounding_factor_full_when_term_present_in_title():
    article = Article(title="Beşiktaş kazandı", source="BBC", url="u", content="içerik")
    assert NewsService._grounding_factor(["Beşiktaş"], article) == 1.0


def test_grounding_factor_full_when_term_present_only_in_content():
    article = Article(title="Maç sonucu", source="BBC", url="u", content="Beşiktaş sahadan galip ayrıldı")
    assert NewsService._grounding_factor(["Beşiktaş"], article) == 1.0


def test_grounding_factor_penalized_when_term_absent():
    article = Article(title="Filenin Sultanları kazandı", source="BBC", url="u", content="voleybol maçı")
    assert NewsService._grounding_factor(["Beşiktaş"], article) == 0.3


def test_grounding_factor_case_insensitive_dotted_i_safe():
    # dotted-İ dersi: sorgudaki "İstanbul" makaledeki "istanbul" ile eşleşmeli
    article = Article(title="istanbulda etkinlik", source="BBC", url="u", content="içerik")
    assert NewsService._grounding_factor(["İstanbul"], article) == 1.0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `venv\Scripts\python.exe -m pytest tests/application/test_news_service.py -v -k "distinguishing_query_terms or grounding_factor"`
Expected: FAIL — `AttributeError: type object 'NewsService' has no attribute '_distinguishing_query_terms'`

- [ ] **Step 3: Write minimal implementation**

`src/application/services/news_service.py` — modül sabitleri bloğuna
(`_DOUBLE_HIT_BONUS` satırının yanına) ekle:

```python
# Sorgudaki özel isim (grounding terimi) hiçbir adayda literal geçmiyorsa
# uygulanan çarpımsal ceza — sert filtre DEĞİL, fail-open: en yüksek semantik
# skorlu sonuç yine de (düşük skorla) görünür kalır.
_GROUNDING_PENALTY = 0.3
```

`_lower_tr_safe`'in hemen altına iki yeni staticmethod ekle:

```python
    @staticmethod
    def _distinguishing_query_terms(query: str) -> List[str]:
        """Sorgudaki özel isim adaylarını çıkarır — büyük harfle başlayan TÜM
        kelimeler (cümle başı DAHİL — bu uygulamadaki sorgular tam cümle
        değil, konu-önce yazılıyor: "Beşiktaş maçı saat kaçta" gibi, özel isim
        genelde İLK kelime; cümle-başını hariç tutmak dünkü canlı bug'ın tam
        senaryosunu kaçırırdı). Sentence-initial yanlış-pozitif riski
        (ör. "Dün ne oldu") kabul edildi — ceza sert değil çarpımsal
        (`_GROUNDING_PENALTY`, sıfır değil), en fazla bir sonucu geriye iter."""
        terms = []
        for w in query.split():
            stripped = w.strip(".,!?;:\"'()")
            if stripped and stripped[0].isupper():
                terms.append(stripped)
        return terms

    @staticmethod
    def _grounding_factor(distinguishing_terms: List[str], article: Article) -> float:
        """Sorgudaki özel isim(ler) bu makalede LİTERAL olarak geçiyor mu.
        Geçmiyorsa `_GROUNDING_PENALTY` çarpanı uygulanır — dünkü "maç" bug'ının
        (semantik olarak benzer ama alakasız içerik) kök nedenini kapatır."""
        if not distinguishing_terms:
            return 1.0
        text = NewsService._lower_tr_safe(f"{article.title} {article.content}")
        for term in distinguishing_terms:
            if re.search(r"\b" + re.escape(NewsService._lower_tr_safe(term)), text):
                return 1.0
        return _GROUNDING_PENALTY
```

- [ ] **Step 4: Run test to verify it passes**

Run: `venv\Scripts\python.exe -m pytest tests/application/test_news_service.py -v -k "distinguishing_query_terms or grounding_factor"`
Expected: 10 passed

- [ ] **Step 5: Commit**

```bash
git add src/application/services/news_service.py tests/application/test_news_service.py
git commit -m "feat: sorgu-varlık doğrulaması yardımcıları (_distinguishing_query_terms, _grounding_factor)"
```

---

### Task 4: `hybrid_search`'e grounding + credibility + trust_score entegrasyonu

**Files:**
- Modify: `src/application/services/news_service.py:206-352` (`hybrid_search`)
- Modify: `src/domain/schemas/news_schema.py` (`SearchResult`)
- Test: `tests/application/test_news_service.py`

**Interfaces:**
- Consumes: `_distinguishing_query_terms`/`_grounding_factor` (Task 3),
  `compute_trust_score` (Task 1), `self.repository.get_articles_by_ids(ids: List[int]) -> List[Article]` (mevcut)
- Produces: `hybrid_search()` sonuç dict'lerine iki yeni anahtar:
  `trust_score: int`, skor formülüne iki yeni çarpan.

- [ ] **Step 1: Write the failing test**

```python
# tests/application/test_news_service.py — mevcut hybrid_search test
# bloğuna ekle. Dosyanın üstünde zaten bir `make_service_with_search()`
# helper'ı var (mock_repo + mock_search döner) — onu kullan.

def test_hybrid_search_penalizes_semantic_result_missing_query_entity():
    """Dünkü 'maç' bug'ı: yüksek semantik skorlu ama sorgudaki özel ismi
    (Beşiktaş) içermeyen bir sonuç, düşük semantik skorlu ama özel ismi
    içeren bir sonucun ALTINA düşmeli."""
    service, mock_repo, mock_search = make_service_with_search()

    off_topic = make_article("https://x.com/1")
    off_topic.id = 1
    off_topic.title = "Filenin Sultanları kazandı"
    off_topic.content = "voleybol maçı heyecanı"

    on_topic = make_article("https://x.com/2")
    on_topic.id = 2
    on_topic.title = "Beşiktaş kazandı"
    on_topic.content = "futbol maçı sonucu"

    mock_search.search.return_value = [
        {"id": "1", "title": off_topic.title, "summary": "", "source": "BBC", "url": off_topic.url, "score": 0.85, "published_at": None},
        {"id": "2", "title": on_topic.title, "summary": "", "source": "BBC", "url": on_topic.url, "score": 0.50, "published_at": None},
    ]
    mock_repo.keyword_search.return_value = []
    mock_repo.get_articles_by_ids.return_value = [off_topic, on_topic]

    results = service.hybrid_search("Beşiktaş maçı saat kaçta", n_results=5)

    scores = {r["id"]: r["score"] for r in results}
    assert scores["2"] > scores["1"]


def test_hybrid_search_no_distinguishing_term_leaves_ranking_unchanged():
    """Sorguda özel isim yoksa (ör. 'futbol haberleri') grounding hiç devreye
    girmemeli — mevcut sıralama davranışı bozulmamalı."""
    service, mock_repo, mock_search = make_service_with_search()
    art = make_article("https://x.com/1")
    art.id = 1
    mock_search.search.return_value = [
        {"id": "1", "title": art.title, "summary": "", "source": "BBC", "url": art.url, "score": 0.7, "published_at": None},
    ]
    mock_repo.keyword_search.return_value = []
    mock_repo.get_articles_by_ids.return_value = [art]

    results = service.hybrid_search("futbol haberleri", n_results=5)

    assert results[0]["score"] == 0.7  # credibility_score None -> 0.85 çarpanı... bkz. alttaki not


def test_hybrid_search_low_credibility_source_dampened_not_zeroed():
    service, mock_repo, mock_search = make_service_with_search()
    art = make_article("https://x.com/1")
    art.id = 1
    art.credibility_score = 0.0
    mock_search.search.return_value = [
        {"id": "1", "title": art.title, "summary": "", "source": "BBC", "url": art.url, "score": 0.8, "published_at": None},
    ]
    mock_repo.keyword_search.return_value = []
    mock_repo.get_articles_by_ids.return_value = [art]

    results = service.hybrid_search("haberler", n_results=5)

    assert 0 < results[0]["score"] < 0.8  # geriye düştü ama sıfırlanmadı


def test_hybrid_search_results_include_trust_score():
    service, mock_repo, mock_search = make_service_with_search()
    art = make_article("https://x.com/1")
    art.id = 1
    art.quality_score = 1.0
    art.credibility_score = 1.0
    art.corroboration_count = 10
    mock_search.search.return_value = [
        {"id": "1", "title": art.title, "summary": "", "source": "BBC", "url": art.url, "score": 0.9, "published_at": None},
    ]
    mock_repo.keyword_search.return_value = []
    mock_repo.get_articles_by_ids.return_value = [art]

    results = service.hybrid_search("haberler", n_results=5)

    assert results[0]["trust_score"] == 100


def test_hybrid_search_get_articles_by_ids_failure_is_fail_open():
    """Article fetch'i patlarsa arama çökmemeli, sadece grounding/credibility/
    trust_score nötr değerlere düşmeli."""
    service, mock_repo, mock_search = make_service_with_search()
    mock_search.search.return_value = [
        {"id": "1", "title": "Bir haber", "summary": "", "source": "BBC", "url": "u", "score": 0.6, "published_at": None},
    ]
    mock_repo.keyword_search.return_value = []
    mock_repo.get_articles_by_ids.side_effect = Exception("db down")

    results = service.hybrid_search("haberler", n_results=5)

    assert len(results) == 1
    assert results[0]["trust_score"] == 40  # None/None/0 nötr varsayılan
```

**Not:** `test_hybrid_search_no_distinguishing_term_leaves_ranking_unchanged`
`credibility_score=None` (mock_article varsayılanı) için `0.85` çarpanı
bekliyor gibi görünse de, `credibility_score` mock `Article`'da `None` ise
`0.7 + 0.3*0.5 = 0.85` çarpanı UYGULANACAK — yani `0.7 * 0.85 = 0.595` çıkar,
`0.7` DEĞİL. **Bu testin beklenen değerini `0.595` olarak yaz** (yukarıdaki
`assert results[0]["score"] == 0.7` satırını `assert results[0]["score"] ==
0.595` ile DEĞİŞTİR) — yorum satırı testin NEDEN 0.7 çıkmadığını açıklamak
için bırakıldı, gerçek implementasyonda credibility her zaman devrede.

- [ ] **Step 2: Run test to verify it fails**

Run: `venv\Scripts\python.exe -m pytest tests/application/test_news_service.py -v -k "hybrid_search_penalizes or hybrid_search_no_distinguishing or hybrid_search_low_credibility or hybrid_search_results_include_trust or hybrid_search_get_articles_by_ids_failure"`
Expected: FAIL — ilk test `AssertionError` (sıralama henüz değişmedi), diğerleri
`KeyError: 'trust_score'`

- [ ] **Step 3: Write minimal implementation**

`src/application/services/news_service.py`'nin üst importlarına ekle:

```python
from src.domain.scoring.trust import compute_trust_score
```

`hybrid_search`'ün başında, `relevance_terms = self._canonical_terms(query)`
satırının hemen altına ekle:

```python
        distinguishing_terms = self._distinguishing_query_terms(query)
```

`combined = []` satırından HEMEN ÖNCE (yani `keyword_by_id` doldurulduktan
sonra, döngüden önce) ekle:

```python
        candidate_ids = set(semantic_by_id) | set(keyword_by_id)
        candidate_ids_int: List[int] = []
        for cid in candidate_ids:
            try:
                candidate_ids_int.append(int(cid))
            except (TypeError, ValueError):
                continue
        try:
            fetched = self.repository.get_articles_by_ids(candidate_ids_int) if candidate_ids_int else []
        except Exception as e:
            logger.warning("Grounding/credibility için makale çekimi başarısız, nötr değerlerle devam: %s", e)
            fetched = []
        articles_by_id = {str(a.id): a for a in fetched}
```

`combined = []` bloğundaki mevcut `for article_id in set(semantic_by_id) |
set(keyword_by_id):` satırını `for article_id in candidate_ids:` olarak
değiştir (aynı küme, tekrar hesaplamaya gerek yok).

`relevance = min(round(base + bonus, 4), 1.0)` ile `data["score"] = final`
arasındaki mevcut üç satırı şu şekilde genişlet:

```python
            relevance = min(round(base + bonus, 4), 1.0)
            recency = self._recency_factor(date_value)

            matched_article = articles_by_id.get(article_id)
            grounding = self._grounding_factor(distinguishing_terms, matched_article) if matched_article else 1.0
            cred = matched_article.credibility_score if matched_article and matched_article.credibility_score is not None else 0.5
            credibility_factor = 0.7 + 0.3 * cred

            final = round(relevance * self._decay_factor(recency) * grounding * credibility_factor, 4)

            data["score"] = final
            data["created_at"] = date_value
            data["_recency_factor"] = recency
            data["trust_score"] = compute_trust_score(
                matched_article.quality_score if matched_article else None,
                matched_article.credibility_score if matched_article else None,
                matched_article.corroboration_count if matched_article else 0,
            )
            combined.append(data)
```

(Eski `final = round(relevance * self._decay_factor(recency), 4)` satırı
SİLİNİR, yerine yukarıdaki genişletilmiş satır gelir.)

`src/domain/schemas/news_schema.py`'de `SearchResult`'a alan ekle:

```python
class SearchResult(BaseModel):
    id: str
    title: str
    summary: str
    source: str
    url: str
    score: float
    trust_score: int = 0
    created_at: Optional[datetime] = None
```

- [ ] **Step 3.5 (ZORUNLU): Paylaşılan test helper'larına varsayılan ekle**

`mock_repo` düz bir `MagicMock()` — `get_articles_by_ids`'i özel olarak set
ETMEYEN mevcut testlerde bu çağrı otomatik-oluşan bir `MagicMock` döner,
`MagicMock` `__iter__` desteklemez, `{str(a.id): a for a in fetched}` satırı
`TypeError: object is not iterable` ile PATLAR. `tests/application/
test_news_service.py`'nin başındaki `make_service()` fonksiyonuna (satır
14-25 civarı, `mock_repo.bulk_exists.return_value = set()` satırının hemen
altına) şu satırı ekle:

```python
    mock_repo.get_articles_by_ids.return_value = []
```

`make_service_with_search()` zaten `make_service()`'i çağırıp `mock_repo`'yu
aynen kullanıyor (satır 96-100), o yüzden AYRICA bir değişiklik gerekmez —
tek satırlık bu ekleme HER İKİ helper'ı da kapsar. Bu, `get_articles_by_ids`'i
özel olarak set etmeyen mevcut testlerde `fetched = []` → `articles_by_id =
{}` → tüm çarpanlar nötr (`grounding=1.0`, `credibility_factor=0.85`) demek —
eski skorlar artık `* 0.85` ile küçülüyor.

- [ ] **Step 4: Run test to verify it passes**

Run: `venv\Scripts\python.exe -m pytest tests/application/test_news_service.py -v`
Expected: Yeni testler PASS. Mevcut `hybrid_search` testlerinden SAYISAL bir
skor sabiti bekleyenler (`assert results[0]["score"] == X` gibi — `credibility_
score=None` olduğu için artık `credibility_factor=0.85` uygulanıyor) FAIL
edecek. **Bunları düzelt:** her başarısız assertion'ın beklenen değerini
`X * 0.85` ile güncelle (yuvarlama: `round(eski_X * 0.85, 4)` — `hybrid_search`
zaten `round(..., 4)` kullanıyor, aynı hassasiyeti koru). Bu bir regresyon
DEĞİL — davranış aynı SIRALAMADA kalıyor, sadece mutlak skor sayısı yeni
credibility çarpanını yansıtacak şekilde küçülüyor. Sıralama/eşitlik/karşılaştırma
bekleyen testler (`>`, `<`, `sorted` sırası) muhtemelen HİÇ değişmeden geçer.

- [ ] **Step 5: Commit**

```bash
git add src/application/services/news_service.py src/domain/schemas/news_schema.py tests/application/test_news_service.py
git commit -m "feat: hybrid_search'e sorgu-varlık doğrulaması + credibility fold-in + trust_score"
```

---

### Task 5: `get_story_cluster`'a trust_score entegrasyonu

**Files:**
- Modify: `src/application/services/news_service.py:720-780` (`get_story_cluster`)
- Modify: `src/domain/schemas/news_schema.py` (`StorySource`)
- Test: `tests/application/test_news_service.py`

**Interfaces:**
- Consumes: `compute_trust_score` (Task 1), `self.repository.get_articles_by_ids` (mevcut)
- Produces: `get_story_cluster()` dönüşündeki her `sources[i]` dict'ine
  `trust_score: int`.

- [ ] **Step 1: Write the failing test**

```python
# tests/application/test_news_service.py — get_story_cluster test bloğuna ekle

def test_get_story_cluster_sources_include_trust_score():
    service, mock_repo, mock_search = make_service_with_search()
    target = make_article("https://x.com/target")
    target.id = 1
    target.entities = {"persons": [], "organizations": ["Beşiktaş"], "locations": []}
    mock_repo.get_article_by_id.return_value = target

    corroborating = make_article("https://x.com/2")
    corroborating.id = 2
    corroborating.quality_score = 0.8
    corroborating.credibility_score = 0.9
    corroborating.corroboration_count = 5
    corroborating.entities = {"persons": [], "organizations": ["Beşiktaş"], "locations": []}

    mock_search.find_similar.return_value = []
    mock_repo.get_recent_articles_with_entities.return_value = [corroborating]
    mock_repo.get_articles_by_ids.return_value = [corroborating]

    result = service.get_story_cluster(1)

    assert len(result["sources"]) == 1
    assert result["sources"][0]["trust_score"] == 100  # 0.8/0.9/5(tavanlı) -> yuvarlanınca 100
```

**Not:** `_find_corroborating_articles`'in gerçek eşik/skor mantığı için
`corroborating`'in `target` ile paylaştığı entity'nin (`"Beşiktaş"`) aday
havuzunda (`get_recent_articles_with_entities`) yeterince nadir olması
gerekir (`_GENERIC_ENTITY_SOURCE_FLOOR = 4`) — tek adaylı bu test fixture'ında
otomatik sağlanıyor (sadece 1 makalede geçiyor, 4'ün altında, ayırt edici
sayılır).

- [ ] **Step 2: Run test to verify it fails**

Run: `venv\Scripts\python.exe -m pytest tests/application/test_news_service.py -v -k get_story_cluster_sources_include_trust_score`
Expected: FAIL — `KeyError: 'trust_score'`

- [ ] **Step 3: Write minimal implementation**

`src/application/services/news_service.py`'de `get_story_cluster`'ın gövdesi
(`combined: dict = {s["id"]: s for s in verified_semantic}` satırından
`return {"article_id": article_id, "sources": sources}` satırına kadar)
şu şekilde değişir:

```python
        try:
            semantic_articles = self.repository.get_articles_by_ids([s["id"] for s in verified_semantic]) if verified_semantic else []
        except Exception as e:
            logger.warning("Story cluster trust_score için makale çekimi başarısız: %s", e)
            semantic_articles = []
        semantic_articles_by_id = {a.id: a for a in semantic_articles}

        combined: dict = {}
        for s in verified_semantic:
            a = semantic_articles_by_id.get(s["id"])
            combined[s["id"]] = {
                **s,
                "trust_score": compute_trust_score(
                    a.quality_score if a else None,
                    a.credibility_score if a else None,
                    a.corroboration_count if a else 0,
                ),
            }

        if target:
            for cand, score in self._find_corroborating_articles(target):
                combined.setdefault(cand.id, {
                    "id": cand.id, "title": cand.title, "source": cand.source,
                    "url": cand.url, "score": score,
                    "trust_score": compute_trust_score(cand.quality_score, cand.credibility_score, cand.corroboration_count),
                })

        sources = sorted(combined.values(), key=lambda s: s["score"], reverse=True)[:limit]
        return {"article_id": article_id, "sources": sources}
```

`src/domain/schemas/news_schema.py`'de `StorySource`'a alan ekle:

```python
class StorySource(BaseModel):
    id: int
    title: str
    source: str
    url: str
    score: float
    trust_score: int = 0
```

- [ ] **Step 4: Run test to verify it passes**

Run: `venv\Scripts\python.exe -m pytest tests/application/test_news_service.py tests/adapters/test_news_repository.py -v`
Expected: TÜM testler PASS — Task 4'te `make_service()`'e eklenen
`mock_repo.get_articles_by_ids.return_value = []` varsayılanı burada da
devreye girer (aynı `mock_repo`), mevcut `get_story_cluster` testlerinde
`trust_score` nötr `40` çıkar; skor SIRALAMASI değişmez çünkü `trust_score`
sıralama anahtarı DEĞİL, sadece görüntü alanı.

- [ ] **Step 5: Commit**

```bash
git add src/application/services/news_service.py src/domain/schemas/news_schema.py tests/application/test_news_service.py
git commit -m "feat: get_story_cluster kaynaklarına trust_score"
```

---

### Task 6: Frontend — güven rozeti (`NewsCard`)

**Files:**
- Modify: `frontend/lib/types.ts`
- Modify: `frontend/components/NewsCard.tsx`

**Interfaces:**
- Consumes: `Article.trust_score`, `SearchResult.trust_score`,
  `StorySource.trust_score` (Task 1-5, backend zaten dolduruyor)

- [ ] **Step 1: Tip tanımlarını güncelle**

`frontend/lib/types.ts` — üç interface'e `trust_score?: number;` ekle:

```typescript
export interface Article {
  // ... mevcut alanlar ...
  corroboration_count?: number;
  trust_score?: number;
  created_at: string;
  published_at?: string;
}
```

```typescript
export interface SearchResult {
  // ... mevcut alanlar ...
  score: number;
  trust_score?: number;
  created_at: string;
}
```

```typescript
export interface StorySource {
  id: number;
  title: string;
  source: string;
  url: string;
  score: number;
  trust_score?: number;
}
```

- [ ] **Step 2: `NewsCard.tsx`'e breakdown metni üreten yardımcı fonksiyon ekle**

Dosyanın üstündeki `corroborationText` fonksiyonunun HEMEN ALTINA ekle
(aynı dosya-lokal desen, `lib/i18n.ts`'e yeni statik anahtar GEREKMİYOR —
yüzdeler backend'deki `_QUALITY_WEIGHT`/`_CREDIBILITY_WEIGHT`/
`_CORROBORATION_WEIGHT` sabitlerinin (0.35/0.45/0.20) elle senkronize
edilmiş bir kopyası):

```typescript
// Güven rozeti breakdown'ı (arama skoru + güven rozeti tasarımı) — backend'deki
// domain/scoring/trust.py::compute_trust_score ağırlıklarıyla (0.35/0.45/0.20)
// elle senkronize. Ağırlıklar değişirse burası da güncellenmeli.
function trustScoreText(score: number, lang: "TR" | "EN"): string {
  if (lang === "TR") {
    return `${score}/100 — %45 kaynak güvenilirliği, %35 içerik kalitesi, %20 çoklu kaynak doğrulaması`;
  }
  return `${score}/100 — 45% source credibility, 35% content quality, 20% multi-source corroboration`;
}
```

- [ ] **Step 3: Mevcut quality-only rozeti kompozit rozetle DEĞİŞTİR**

`frontend/components/NewsCard.tsx`'teki şu mevcut bloğu:

```tsx
          {article.quality_score != null && (
            <span className="badge" style={{ background: "rgba(0,0,0,.25)", color: "var(--text3)",
                                             borderColor: "var(--border)" }}>
              ✦ {(article.quality_score * 100).toFixed(0)}
            </span>
          )}
```

şununla DEĞİŞTİR:

```tsx
          {article.trust_score != null && (
            <span className="badge" title={trustScoreText(article.trust_score, lang)}
                  style={{ background: "rgba(0,0,0,.25)", color: "var(--text3)",
                           borderColor: "var(--border)" }}>
              ✦ {article.trust_score}
            </span>
          )}
```

(`🔗 corroboration_count` rozeti AYNEN kalır — ham sayı olarak ayrı, farklı
bir bilgi taşıyor, kaldırılmıyor.)

- [ ] **Step 4: Tip kontrolü + build doğrulaması**

Run: `cd frontend && npm run build`
Expected: hatasız tamamlanır (frontend container ÇALIŞIRKEN host'ta ÇALIŞTIRMA
— CLAUDE.md "npm run build" gotcha'sı; önce `docker compose stop frontend`
gerekebilir, ya da sadece `npx tsc --noEmit` ile tip kontrolü yeterli).

- [ ] **Step 5: Commit**

```bash
git add frontend/lib/types.ts frontend/components/NewsCard.tsx
git commit -m "feat: NewsCard'da görünür güven rozeti (quality-only rozetin yerine)"
```

---

## Self-Review Notu (plan yazarı için, uygulama öncesi referans)

- **Spec kapsaması:** A) grounding+credibility → Task 3+4. B) trust_score
  hesabı → Task 1. B) NewsResponse/SearchResult/StorySource'ta görünürlük →
  Task 2/4/5. B) frontend rozet+breakdown → Task 6. Hepsi kapsandı.
- **`or 0.5` bug'ı:** Task 1/3/4/5'in HİÇBİRİNDE kullanılmadı, hepsi açık
  `is not None` kontrolü kullanıyor — spec'teki düzeltme plana doğru taşındı.
- **Tip tutarlılığı:** `_grounding_factor(distinguishing_terms: List[str],
  article: Article) -> float` imzası Task 3'te tanımlanıp Task 4'te AYNEN
  kullanılıyor. `compute_trust_score(quality_score, credibility_score,
  corroboration_count) -> int` imzası Task 1'de tanımlanıp Task 2/4/5'in
  HEPSİNDE aynı sırayla çağrılıyor.
