# Arama İlişkisel Sorgu Genişletme Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Arama sorgusuna ("İstanbul", "futbol") LLM tabanlı ilişkili ek
terimler ("Beykoz", "Beşiktaş") eklemek — semantik taraf dokunulmadan,
sadece keyword tarafına düşük ağırlıkla, cache'li ve tamamen fail-open.

**Architecture:** Yeni `QueryExpansionPort` (domain) + `GroqQueryExpander`
(Groq'a küçük bir prompt) + `CachingQueryExpander` decorator (mevcut
`CachePort`'u sarar). `NewsService.hybrid_search` bu port'u opsiyonel bir
bağımlılık olarak alır; genişletilmiş terimler SQL aday havuzuna ve
`_keyword_relevance`'a ikincil (düşük ağırlıklı) bir terim seti olarak
eklenir.

**Tech Stack:** Python 3.13, FastAPI, Groq REST API (`openai/gpt-oss-20b`),
Redis (mevcut `CachePort`/`RedisAdapter`/`NullCacheAdapter`), pytest +
`unittest.mock`.

**Spec:** `docs/superpowers/specs/2026-08-20-arama-iliskisel-genisletme-design.md`

## Global Constraints

- Her hata yolu (429, timeout, bozuk JSON, model kaldırılmış, cache hatası)
  **boş liste** ile sonuçlanır — hiçbir exception `hybrid_search`'e sızmaz.
- Semantik (ChromaDB) tarafı bu değişiklikle **hiç dokunulmaz**.
- `_keyword_relevance`'ın mevcut testleri (tek-parametreli çağrılar) **davranış
  değiştirmeden** geçmeye devam etmeli — yeni parametre opsiyonel.
- `NewsService.__init__`'e eklenen `query_expander` opsiyonel — verilmezse
  (`None`) `hybrid_search`'ün mevcut tüm testleri değişmeden geçmeli.
- Cache key: `f"qexp:{query.strip().lower()}"`. TTL: dolu sonuç 30 gün
  (`30*24*60*60` sn), boş sonuç 1 saat (`60*60` sn).
- `_EXPANSION_WEIGHT = 0.4` (ikincil terim skoru asıl skoru domine edemez).
- DB migration YOK — tamamen stateless (cache Redis'te, Postgres'e hiç yazılmaz).

---

### Task 1: `QueryExpansionPort` (domain port)

**Files:**
- Create: `src/domain/ports/query_expansion_port.py`

**Interfaces:**
- Consumes: yok (saf arayüz tanımı).
- Produces: `QueryExpansionPort.expand(query: str) -> List[str]` — sonraki
  tüm task'lar bu imzayı kullanır.

- [ ] **Step 1: Port dosyasını yaz**

```python
"""Sorgu genişletme port'u — arama sorgusuna ilişkili ek terimler üretir
("İstanbul" → "Beykoz", "futbol" → "Beşiktaş" gibi). Somut implementasyon:
GroqQueryExpander (+ CachingQueryExpander decorator).
"""

from abc import ABC, abstractmethod
from typing import List


class QueryExpansionPort(ABC):
    @abstractmethod
    def expand(self, query: str) -> List[str]: ...
```

- [ ] **Step 2: İçe aktarımın çalıştığını doğrula**

Run: `venv\Scripts\python.exe -c "from src.domain.ports.query_expansion_port import QueryExpansionPort; print('ok')"`
Expected: `ok` yazdırır, hata yok.

- [ ] **Step 3: Commit**

```bash
git add src/domain/ports/query_expansion_port.py
git commit -m "feat: QueryExpansionPort arayüzü eklendi"
```

---

### Task 2: `GroqQueryExpander` adapter (TDD)

**Files:**
- Create: `src/adapters/analysis/groq_query_expander.py`
- Test: `tests/adapters/test_groq_query_expander.py`

**Interfaces:**
- Consumes: `QueryExpansionPort` (Task 1), `settings.groq_api_key`
  (`src/infrastructure/config/settings.py`, zaten var).
- Produces: `GroqQueryExpander().expand(query: str) -> List[str]` — Task 3
  ve Task 4 bunu somut olarak sarmalayacak.

- [ ] **Step 1: Testleri yaz**

```python
"""tests/adapters/test_groq_query_expander.py"""
from unittest.mock import patch, MagicMock
from src.adapters.analysis.groq_query_expander import GroqQueryExpander


def _mock_response(status_code=200, content=None, text=""):
    r = MagicMock()
    r.status_code = status_code
    r.text = text
    if content is not None:
        r.json.return_value = {"choices": [{"message": {"content": content}}]}
    return r


def test_expand_returns_terms_on_success():
    resp = _mock_response(200, content='{"terms": ["Beykoz", "Kadıköy", "Üsküdar"]}')
    with patch("requests.post", return_value=resp) as mock_post:
        expander = GroqQueryExpander()
        result = expander.expand("istanbul")
    assert result == ["Beykoz", "Kadıköy", "Üsküdar"]
    mock_post.assert_called_once()


def test_expand_extracts_json_even_with_surrounding_text():
    resp = _mock_response(200, content='Elbette:\n{"terms": ["Beşiktaş", "Fenerbahçe"]}\nUmarım yardımcı olur.')
    with patch("requests.post", return_value=resp):
        result = GroqQueryExpander().expand("futbol")
    assert result == ["Beşiktaş", "Fenerbahçe"]


def test_expand_returns_empty_on_non_200():
    resp = _mock_response(429, text="rate limit")
    with patch("requests.post", return_value=resp):
        result = GroqQueryExpander().expand("istanbul")
    assert result == []


def test_expand_returns_empty_on_malformed_json():
    resp = _mock_response(200, content="bu JSON değil, düz metin")
    with patch("requests.post", return_value=resp):
        result = GroqQueryExpander().expand("istanbul")
    assert result == []


def test_expand_returns_empty_on_request_exception():
    with patch("requests.post", side_effect=TimeoutError("timeout")):
        result = GroqQueryExpander().expand("istanbul")
    assert result == []


def test_expand_returns_empty_for_blank_query():
    with patch("requests.post") as mock_post:
        result = GroqQueryExpander().expand("   ")
    assert result == []
    mock_post.assert_not_called()


def test_expand_limits_to_six_terms():
    terms = [f"terim{i}" for i in range(10)]
    resp = _mock_response(200, content=f'{{"terms": {terms!r}}}'.replace("'", '"'))
    with patch("requests.post", return_value=resp):
        result = GroqQueryExpander().expand("test")
    assert len(result) <= 6


def test_expand_filters_non_string_terms():
    resp = _mock_response(200, content='{"terms": ["Beykoz", 123, null, "  ", "Kadıköy"]}')
    with patch("requests.post", return_value=resp):
        result = GroqQueryExpander().expand("istanbul")
    assert result == ["Beykoz", "Kadıköy"]
```

- [ ] **Step 2: Testleri çalıştırıp fail ettiğini doğrula**

Run: `venv\Scripts\python.exe -m pytest tests/adapters/test_groq_query_expander.py -v`
Expected: `ModuleNotFoundError: No module named 'src.adapters.analysis.groq_query_expander'`

- [ ] **Step 3: Adapter'ı yaz**

```python
"""src/adapters/analysis/groq_query_expander.py

Groq tabanlı sorgu genişletme adapter'ı — arama sorgusuyla ilişkili ek
terimler üretir ("istanbul" → ilçeleri, "futbol" → büyük takımlar).

Spike'ta (20 Ağu 2026, bkz. spec) doğrulandı: "istanbul" için gerçek ilçe
isimleri üretti (Fatih, Beyoğlu, Kadıköy...), 0.8sn. Her hata yolu
(429/timeout/bozuk JSON/model kaldırılmış) boş liste ile sonuçlanır —
arama ASLA bu adaptör yüzünden bozulmaz (projenin "Exception'ları yut,
logla, fallback dön" kuralı).
"""

import json
import logging
import re
from typing import List

import requests

from src.domain.ports.query_expansion_port import QueryExpansionPort
from src.infrastructure.config.settings import settings

logger = logging.getLogger(__name__)

_PROMPT_TEMPLATE = """Sen bir Türkçe haber arama motorunun sorgu genişletme asistanısın.
Kullanıcı "{query}" diye arattı. Bu sorguyla ANLAMCA/İLİŞKİSEL olarak yakın,
haber arama sonuçlarını zenginleştirecek 3-6 ek terim üret.

Kurallar:
- Sorgu bir şehir/il ise: bilinen büyük ilçelerini/semtlerini ekle.
- Sorgu bir spor dalıysa: o daldaki büyük/bilinen takım isimlerini ekle.
- Sorgu bir ekonomik/siyasi kavramsa: ilgili kurum/kişi/parti isimlerini ekle.
- Sorgunun kendisini tekrar ETME, SADECE yeni terimler ver.
- Emin değilsen az terim üret, uydurma/yanlış bilgi verme.

SADECE şu JSON formatında yanıt ver, başka hiçbir metin ekleme:
{{"terms": ["terim1", "terim2", ...]}}

Sorgu: {query}"""

_MAX_TERMS = 6


class GroqQueryExpander(QueryExpansionPort):
    def __init__(self):
        self.api_key = settings.groq_api_key
        self.model = "openai/gpt-oss-20b"
        self.api_url = "https://api.groq.com/openai/v1/chat/completions"

    def expand(self, query: str) -> List[str]:
        if not query or not query.strip():
            return []
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": _PROMPT_TEMPLATE.format(query=query)}],
            "temperature": 0.3,
            "max_tokens": 300,
            "reasoning_effort": "low",
        }
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        try:
            r = requests.post(self.api_url, headers=headers, json=payload, timeout=10)
            if r.status_code != 200:
                logger.warning("Sorgu genişletme başarısız (status=%d): %s", r.status_code, r.text[:200])
                return []
            content = r.json()["choices"][0]["message"]["content"]
            match = re.search(r"\{.*\}", content, re.DOTALL)
            parsed = json.loads(match.group(0)) if match else json.loads(content)
            terms = parsed.get("terms", [])
            clean = [t.strip() for t in terms if isinstance(t, str) and t.strip()]
            return clean[:_MAX_TERMS]
        except Exception as e:
            logger.warning("Sorgu genişletme hatası: %s", e)
            return []
```

- [ ] **Step 4: Testleri çalıştırıp geçtiğini doğrula**

Run: `venv\Scripts\python.exe -m pytest tests/adapters/test_groq_query_expander.py -v`
Expected: 8 test PASS.

- [ ] **Step 5: Commit**

```bash
git add src/adapters/analysis/groq_query_expander.py tests/adapters/test_groq_query_expander.py
git commit -m "feat: GroqQueryExpander — LLM tabanlı sorgu genişletme adapter'ı"
```

---

### Task 3: `CachingQueryExpander` decorator (TDD)

**Files:**
- Create: `src/adapters/analysis/caching_query_expander.py`
- Test: `tests/adapters/test_caching_query_expander.py`

**Interfaces:**
- Consumes: `QueryExpansionPort` (Task 1), `CachePort`
  (`src/domain/ports/cache_port.py`, zaten var: `get(key)`,
  `set(key, value, ttl_seconds=60)`, `delete(key)`).
- Produces: `CachingQueryExpander(inner, cache).expand(query) -> List[str]`
  — Task 4'te `build_query_expander()` bunu üretir.

- [ ] **Step 1: Testleri yaz**

```python
"""tests/adapters/test_caching_query_expander.py"""
from src.adapters.analysis.caching_query_expander import CachingQueryExpander


class _FakeCache:
    """CachePort'un basit, hatasız bir sahte implementasyonu."""
    def __init__(self):
        self.store = {}
        self.set_calls = []

    def get(self, key):
        return self.store.get(key)

    def set(self, key, value, ttl_seconds=60):
        self.store[key] = value
        self.set_calls.append((key, value, ttl_seconds))

    def delete(self, key):
        self.store.pop(key, None)


class _FakeExpander:
    def __init__(self, terms):
        self.terms = terms
        self.call_count = 0

    def expand(self, query):
        self.call_count += 1
        return self.terms


def test_expand_returns_cached_value_without_calling_inner():
    cache = _FakeCache()
    cache.store["qexp:istanbul"] = ["Beykoz", "Kadıköy"]
    inner = _FakeExpander(["farklı bir sonuç"])

    result = CachingQueryExpander(inner, cache).expand("istanbul")

    assert result == ["Beykoz", "Kadıköy"]
    assert inner.call_count == 0


def test_expand_calls_inner_and_caches_on_miss():
    cache = _FakeCache()
    inner = _FakeExpander(["Beşiktaş", "Fenerbahçe"])

    result = CachingQueryExpander(inner, cache).expand("futbol")

    assert result == ["Beşiktaş", "Fenerbahçe"]
    assert inner.call_count == 1
    assert cache.store["qexp:futbol"] == ["Beşiktaş", "Fenerbahçe"]


def test_expand_normalizes_cache_key_case_and_whitespace():
    cache = _FakeCache()
    inner = _FakeExpander(["x"])

    CachingQueryExpander(inner, cache).expand("  İstanbul  ")

    assert "qexp:i̇stanbul" in cache.store or "qexp:istanbul" in cache.store


def test_expand_caches_empty_result_with_short_ttl():
    cache = _FakeCache()
    inner = _FakeExpander([])

    CachingQueryExpander(inner, cache).expand("asdkjf")

    key, value, ttl = cache.set_calls[0]
    assert value == []
    assert ttl == 60 * 60


def test_expand_caches_nonempty_result_with_long_ttl():
    cache = _FakeCache()
    inner = _FakeExpander(["Beykoz"])

    CachingQueryExpander(inner, cache).expand("istanbul")

    key, value, ttl = cache.set_calls[0]
    assert ttl == 30 * 24 * 60 * 60
```

- [ ] **Step 2: Testleri çalıştırıp fail ettiğini doğrula**

Run: `venv\Scripts\python.exe -m pytest tests/adapters/test_caching_query_expander.py -v`
Expected: `ModuleNotFoundError: No module named 'src.adapters.analysis.caching_query_expander'`

- [ ] **Step 3: Decorator'ı yaz**

```python
"""src/adapters/analysis/caching_query_expander.py

QueryExpansionPort'u CachePort ile saran bir decorator — cache hit'te
alttaki (gerçek Groq çağrısı yapan) expander'a hiç gitmez. Dolu sonuç 30
gün, boş sonuç 1 saat cache'lenir (geçici bir Groq arızasını kalıcı "hiç
genişletme yok" damgası yapmamak için). Cache okuma/yazma hatası zaten
CachePort implementasyonlarının (RedisAdapter, NullCacheAdapter) kendi
sorumluluğu — burada ekstra try/except gerekmiyor.
"""

from typing import List

from src.domain.ports.query_expansion_port import QueryExpansionPort
from src.domain.ports.cache_port import CachePort

_TTL_HIT_SECONDS = 30 * 24 * 60 * 60   # 30 gün
_TTL_EMPTY_SECONDS = 60 * 60           # 1 saat


class CachingQueryExpander(QueryExpansionPort):
    def __init__(self, inner: QueryExpansionPort, cache: CachePort):
        self.inner = inner
        self.cache = cache

    def expand(self, query: str) -> List[str]:
        key = f"qexp:{query.strip().lower()}"
        cached = self.cache.get(key)
        if cached is not None:
            return cached
        terms = self.inner.expand(query)
        ttl = _TTL_HIT_SECONDS if terms else _TTL_EMPTY_SECONDS
        self.cache.set(key, terms, ttl_seconds=ttl)
        return terms
```

- [ ] **Step 4: Testleri çalıştırıp geçtiğini doğrula**

Run: `venv\Scripts\python.exe -m pytest tests/adapters/test_caching_query_expander.py -v`
Expected: 5 test PASS.

- [ ] **Step 5: Commit**

```bash
git add src/adapters/analysis/caching_query_expander.py tests/adapters/test_caching_query_expander.py
git commit -m "feat: CachingQueryExpander — sorgu genişletmeyi CachePort ile önbellekler"
```

---

### Task 4: `settings` env var + `build_query_expander()` factory (TDD)

**Files:**
- Modify: `src/infrastructure/config/settings.py` (yeni alan, `search_recency_window_days` alanının yanına ekle)
- Modify: `src/adapters/analysis/factory.py`
- Test: `tests/adapters/test_query_expander_factory.py`

**Interfaces:**
- Consumes: `GroqQueryExpander` (Task 2), `CachingQueryExpander` (Task 3), `CachePort`.
- Produces: `build_query_expander(cache: CachePort) -> Optional[QueryExpansionPort]`
  — Task 7'de `dependencies.py` bunu çağıracak.

- [ ] **Step 1: Testi yaz**

```python
"""tests/adapters/test_query_expander_factory.py"""
from unittest.mock import MagicMock
from src.adapters.analysis import factory
from src.adapters.analysis.caching_query_expander import CachingQueryExpander


def test_build_query_expander_returns_none_when_disabled(monkeypatch):
    monkeypatch.setattr(factory.settings, "search_query_expansion_enabled", False)
    assert factory.build_query_expander(cache=MagicMock()) is None


def test_build_query_expander_returns_caching_decorator_when_enabled(monkeypatch):
    monkeypatch.setattr(factory.settings, "search_query_expansion_enabled", True)
    result = factory.build_query_expander(cache=MagicMock())
    assert isinstance(result, CachingQueryExpander)
```

- [ ] **Step 2: Testi çalıştırıp fail ettiğini doğrula**

Run: `venv\Scripts\python.exe -m pytest tests/adapters/test_query_expander_factory.py -v`
Expected: `AttributeError: module 'src.adapters.analysis.factory' has no attribute 'build_query_expander'`

- [ ] **Step 3: `settings.py`'a env var ekle**

`src/infrastructure/config/settings.py` içinde `search_recency_window_days: int = 30`
satırının hemen altına ekle:

```python
    # false → sorgu genişletme (LLM ile ilişkili terim üretme) komple kapanır;
    # worker/haber analizi etkilenmez, sadece arama eski (genişletmesiz) haline döner.
    search_query_expansion_enabled: bool = True
```

- [ ] **Step 4: `factory.py`'a `build_query_expander` ekle**

`src/adapters/analysis/factory.py`'ın tamamını şu hale getir:

```python
"""Analyzer + sorgu genişletme kompozisyon noktası — Groq birincil, HuggingFace opsiyonel yedek."""
from typing import Optional
from src.adapters.analysis.groq_analyzer import GroqAnalyzer
from src.adapters.analysis.huggingface_analyzer import HuggingFaceAnalyzer
from src.adapters.analysis.fallback_analyzer import FallbackAnalyzer
from src.adapters.analysis.groq_query_expander import GroqQueryExpander
from src.adapters.analysis.caching_query_expander import CachingQueryExpander
from src.domain.ports.analysis_port import AnalysisPort
from src.domain.ports.query_expansion_port import QueryExpansionPort
from src.domain.ports.cache_port import CachePort
from src.infrastructure.config.settings import settings


def build_analyzer() -> AnalysisPort:
    analyzers = [GroqAnalyzer()]
    if settings.huggingface_api_key:
        analyzers.append(HuggingFaceAnalyzer())
    return FallbackAnalyzer(analyzers)


def build_query_expander(cache: CachePort) -> Optional[QueryExpansionPort]:
    """Sorgu genişletme kompozisyon noktası. `cache` dışarıdan verilir —
    dependencies.py'deki tekil CachePort singleton'ı paylaşılsın diye
    (kendi cache'ini yaratırsa tekillik bozulur)."""
    if not settings.search_query_expansion_enabled:
        return None
    return CachingQueryExpander(GroqQueryExpander(), cache)
```

- [ ] **Step 5: Testi çalıştırıp geçtiğini doğrula**

Run: `venv\Scripts\python.exe -m pytest tests/adapters/test_query_expander_factory.py -v`
Expected: 2 test PASS.

- [ ] **Step 6: Commit**

```bash
git add src/infrastructure/config/settings.py src/adapters/analysis/factory.py tests/adapters/test_query_expander_factory.py
git commit -m "feat: SEARCH_QUERY_EXPANSION_ENABLED env var + build_query_expander factory"
```

---

### Task 5: `_keyword_relevance` — ikincil terim desteği (TDD, refactor)

**Files:**
- Modify: `src/application/services/news_service.py:317-353` (`_keyword_relevance`)
- Test: `tests/application/test_news_service.py`

**Interfaces:**
- Consumes: yok (saf fonksiyon değişikliği).
- Produces: `NewsService._keyword_relevance(article, query_terms, secondary_terms=None) -> float`
  — Task 6 `hybrid_search` içinde bunu `secondary_terms=expanded_terms` ile çağıracak.

- [ ] **Step 1: Yeni testleri ekle**

`tests/application/test_news_service.py` içinde, mevcut
`test_keyword_relevance_empty_terms` testinin hemen altına ekle:

```python
def test_keyword_relevance_secondary_terms_add_small_bonus():
    """Sadece ikincil (genişletilmiş) terim geçen makale sıfırdan farklı, ama
    birincil terimin verdiği skordan daha düşük bir skor almalı."""
    article = make_article()
    article.title = "Beykoz'da yeni bir proje açıldı"
    article.summary = None
    article.content = "alakasız içerik"
    relevance = NewsService._keyword_relevance(article, ["istanbul"], secondary_terms=["beykoz"])
    assert 0.0 < relevance < 0.9  # sadece "istanbul" geçseydi 0.9 olurdu


def test_keyword_relevance_primary_always_beats_secondary_only():
    article_primary = make_article()
    article_primary.title = "İstanbul'da toplantı yapıldı"
    article_primary.summary = None
    article_primary.content = "alakasız içerik"

    article_secondary = make_article()
    article_secondary.title = "Beykoz'da toplantı yapıldı"
    article_secondary.summary = None
    article_secondary.content = "alakasız içerik"

    primary_score = NewsService._keyword_relevance(article_primary, ["istanbul"], secondary_terms=["beykoz"])
    secondary_score = NewsService._keyword_relevance(article_secondary, ["istanbul"], secondary_terms=["beykoz"])

    assert primary_score > secondary_score


def test_keyword_relevance_no_secondary_terms_matches_old_behavior():
    article = make_article()
    article.title = "Yapay zeka çağı"
    article.summary = None
    relevance = NewsService._keyword_relevance(article, ["yapay", "zeka"], secondary_terms=None)
    assert relevance == 0.9


def test_keyword_relevance_score_never_exceeds_one():
    article = make_article()
    article.title = "istanbul beykoz"
    article.summary = None
    article.content = ""
    relevance = NewsService._keyword_relevance(article, ["istanbul"], secondary_terms=["beykoz"])
    assert relevance <= 1.0
```

- [ ] **Step 2: Testleri çalıştırıp fail ettiğini doğrula**

Run: `venv\Scripts\python.exe -m pytest tests/application/test_news_service.py -k "secondary" -v`
Expected: `TypeError: _keyword_relevance() got an unexpected keyword argument 'secondary_terms'`

- [ ] **Step 3: `_keyword_relevance`'ı refactor et**

`src/application/services/news_service.py`'de `_keyword_relevance` metodunun
TAMAMINI (mevcut docstring dahil, 317-353. satırlar) şununla değiştir:

```python
    @staticmethod
    def _coverage_score(title: str, summary: str, content: str, terms: List[str]) -> float:
        """Verilen terim listesinin başlık/özet/içerikte kapsama oranı — en
        iyi alan skoru döner (_FIELD_WEIGHTS). `_keyword_relevance` hem
        birincil hem ikincil (genişletme) terimler için bunu paylaşır (DRY)."""
        if not terms:
            return 0.0
        patterns = [re.compile(r"\b" + re.escape(t)) for t in terms]
        n = len(terms)
        title_hits = sum(1 for p in patterns if p.search(title))
        summary_hits = sum(1 for p in patterns if p.search(summary))
        content_hits = sum(1 for p in patterns if p.search(content))
        title_score = (title_hits / n) * _FIELD_WEIGHTS["title"]
        summary_score = (summary_hits / n) * _FIELD_WEIGHTS["summary"]
        content_score = (content_hits / n) * _FIELD_WEIGHTS["content"]
        return max(title_score, summary_score, content_score)

    @staticmethod
    def _keyword_relevance(
        article: Article,
        query_terms: List[str],
        secondary_terms: Optional[List[str]] = None,
    ) -> float:
        """Coverage tabanlı keyword skoru: terimlerin yüzde kaçı hangi alanda geçiyor.

        Alanlar ayrı puanlanır ve en iyisi alınır — başlıkta tam eşleşme,
        içerikte kısmi eşleşmeden her zaman üstündür (_FIELD_WEIGHTS).

        `query_terms` burada `_canonical_terms()`'ın çıktısı olmalı (bir orijinal
        kelime = bir terim) — `_tokenize()`'ın çıktısını (kelime+kök ayrı ayrı)
        VERME, coverage bölenini yapay şişirir (bkz. `_canonical_terms` docstring).

        Eşleşme kelimenin BAŞINDA aranır (`\\bterim`), metnin herhangi bir yerinde
        geçen ham bir alt dizi olarak DEĞİL — kök bir SUFFIX kırpması olduğu için
        orijinal kelimenin çekimli hallerini yakalamak ister ("adana" → kök "ada",
        metinde "adanada" gibi bir çekimi yakalasın), ama ham `t in text` bunu
        kelime sınırı gözetmeden yapıyordu: "ada" kökü "havadan" kelimesinin
        ORTASINDA da eşleşiyor, alakasız haberleri en üst sıraya taşıyordu
        (20 Ağu 2026'da canlıda "Adana" aramasıyla bulundu).

        `secondary_terms` (opsiyonel) — LLM sorgu genişletmesinden gelen
        ilişkili terimler ("İstanbul" → "Beykoz"). Bunlar AYRI bir coverage
        hesabıyla skorlanır ve `_EXPANSION_WEIGHT` (0.4) ile küçültülerek asıl
        skora eklenir — orijinal terimle eşleşen bir haber HER ZAMAN sadece
        genişletilmiş terimle eşleşenden üstte kalır, ama ikincisi de artık
        sıfır değildir (20 Ağu 2026, bkz. spec "arama ilişkisel genişletme").
        """
        title = article.title.lower() if article.title else ""
        summary = article.summary.lower() if article.summary else ""
        content = article.content.lower() if article.content else ""

        base = NewsService._coverage_score(title, summary, content, query_terms)
        secondary = NewsService._coverage_score(title, summary, content, secondary_terms or [])

        total = base + secondary * _EXPANSION_WEIGHT
        return round(min(total, 1.0), 4)
```

Ayrıca dosyanın üstündeki sabitler bloğuna (`_DOUBLE_HIT_BONUS` satırının
hemen altına) ekle:

```python
# LLM sorgu genişletmesinden gelen ikincil terimlerin skor ağırlığı — asıl
# (birincil) eşleşmeyi asla domine etmesin diye 1.0'ın belirgin altında.
_EXPANSION_WEIGHT = 0.4
```

`Optional` zaten dosyanın üstünde `from typing import List, Optional` ile
import edilmiş durumda (mevcut kodda kontrol et, yoksa ekle).

- [ ] **Step 4: TÜM `_keyword_relevance`/`_canonical_terms` testlerini çalıştır**

Run: `venv\Scripts\python.exe -m pytest tests/application/test_news_service.py -k "keyword_relevance or canonical" -v`
Expected: Yeni 4 test dahil, TÜMÜ (eski + yeni) PASS. Eski testlerin
davranışı BİREBİR aynı kalmalı — biri bile FAIL olursa refactor'da bir
sapma var demektir, `_coverage_score` çıktısını eski koddaki ile karşılaştır.

- [ ] **Step 5: Commit**

```bash
git add src/application/services/news_service.py tests/application/test_news_service.py
git commit -m "refactor: _keyword_relevance ikincil (genişletme) terim desteği"
```

---

### Task 6: `NewsService` — `query_expander` bağımlılığı + `hybrid_search` entegrasyonu (TDD)

**Files:**
- Modify: `src/application/services/news_service.py:78-90` (`__init__`)
- Modify: `src/application/services/news_service.py:160-235` (`hybrid_search`)
- Test: `tests/application/test_news_service.py`

**Interfaces:**
- Consumes: `QueryExpansionPort.expand(query) -> List[str]` (Task 1),
  `NewsService._keyword_relevance(article, terms, secondary_terms=None)` (Task 5).
- Produces: `NewsService(..., query_expander: Optional[QueryExpansionPort] = None)`.

- [ ] **Step 1: Yeni testleri ekle**

`tests/application/test_news_service.py`'de `test_hybrid_search_returns_semantic_results`
testinin hemen üstüne (hybrid_search test bloğunun başına) ekle:

```python
def test_hybrid_search_without_expander_matches_old_behavior():
    """query_expander verilmezse davranış eskisiyle BİREBİR aynı kalmalı."""
    service, mock_repo, mock_search = make_service_with_search()
    mock_search.search.return_value = []
    keyword_article = make_article()
    keyword_article.id = 1
    keyword_article.title = "İstanbul'da toplantı"
    keyword_article.summary = None
    mock_repo.keyword_search.return_value = [keyword_article]

    results = service.hybrid_search("istanbul")

    assert len(results) == 1
    mock_repo.keyword_search.assert_called_once()
    called_terms = mock_repo.keyword_search.call_args.kwargs["terms"]
    assert "istanbul" in called_terms


def test_hybrid_search_includes_secondary_match_via_expander():
    """query_expander "beykoz" döndürürse, sadece "Beykoz" geçen (İstanbul
    geçmeyen) bir haber de artık sonuçlarda görünmeli — düşük skorla."""
    mock_repo = MagicMock()
    mock_search = MagicMock()
    mock_expander = MagicMock()
    mock_expander.expand.return_value = ["beykoz"]
    mock_search.search.return_value = []

    beykoz_article = make_article()
    beykoz_article.id = 7
    beykoz_article.title = "Beykoz'da yeni bir proje açıldı"
    beykoz_article.summary = None
    mock_repo.keyword_search.return_value = [beykoz_article]

    service = NewsService(
        repository=mock_repo, analyzer=MagicMock(),
        search_repository=mock_search, query_expander=mock_expander,
    )

    results = service.hybrid_search("istanbul")

    assert len(results) == 1
    assert results[0]["id"] == "7"
    assert 0.0 < results[0]["score"] < 0.9
    mock_expander.expand.assert_called_once_with("istanbul")
    called_terms = mock_repo.keyword_search.call_args.kwargs["terms"]
    assert "beykoz" in called_terms


def test_hybrid_search_expander_failure_falls_back_to_original_query():
    """expand() exception fırlatırsa arama SESSİZCE orijinal sorguyla devam
    etmeli, hybrid_search hiç patlamamalı."""
    mock_repo = MagicMock()
    mock_expander = MagicMock()
    mock_expander.expand.side_effect = RuntimeError("Groq çöktü")

    keyword_article = make_article()
    keyword_article.id = 3
    keyword_article.title = "yapay zeka haberi"
    keyword_article.summary = None
    mock_repo.keyword_search.return_value = [keyword_article]

    service = NewsService(
        repository=mock_repo, analyzer=MagicMock(),
        search_repository=None, query_expander=mock_expander,
    )

    results = service.hybrid_search("yapay zeka")

    assert len(results) == 1
    assert results[0]["id"] == "3"
```

`make_service_with_search()` helper'ının tanımını kontrol et (dosyanın
üstünde olmalı) — eğer `query_expander` parametresi olmadan
`NewsService(...)` çağırıyorsa dokunma, Task 6 Step 3'te `query_expander`
opsiyonel (varsayılan `None`) olacağı için bu helper DEĞİŞMEDEN çalışmaya
devam eder.

- [ ] **Step 2: Testleri çalıştırıp fail ettiğini doğrula**

Run: `venv\Scripts\python.exe -m pytest tests/application/test_news_service.py -k "expander" -v`
Expected: `TypeError: NewsService.__init__() got an unexpected keyword argument 'query_expander'`

- [ ] **Step 3: `__init__`'i güncelle**

`src/application/services/news_service.py:78-90` bloğunu şununla değiştir:

```python
    def __init__(
        self,
        repository: NewsRepositoryPort,
        analyzer: AnalysisPort,
        search_repository=None,
        subscriber_repository: Optional["SubscriberRepositoryPort"] = None,
        email_port: Optional["EmailPort"] = None,
        query_expander: Optional["QueryExpansionPort"] = None,
    ):
        self.repository = repository
        self.analyzer = analyzer
        self.search_repository = search_repository
        self.subscriber_repository = subscriber_repository
        self.email_port = email_port
        self.query_expander = query_expander
```

Dosyanın üstündeki `TYPE_CHECKING` bloğuna ekle:

```python
if TYPE_CHECKING:
    from src.domain.ports.email_port import EmailPort
    from src.domain.ports.subscriber_port import SubscriberRepositoryPort
    from src.domain.ports.query_expansion_port import QueryExpansionPort
```

- [ ] **Step 4: `hybrid_search`'ü güncelle**

`src/application/services/news_service.py:160-193` bloğunu (fonksiyon
başından `keyword_by_id` doldurma bloğunun sonuna kadar) şununla değiştir —
geri kalanı (`combined` birleştirme mantığı, satır 195'ten sonrası)
DOKUNULMADAN aynen kalır:

```python
    def hybrid_search(self, query: str, n_results: int = 10, source: str = None, sentiment: str = None) -> list[dict]:
        """Semantik (ChromaDB) ve keyword (PostgreSQL) aramayı birleştirir.

        Skor = (max(semantik, keyword) + double-hit bonus) * recency çarpanı
        (`_decay_factor` — bugün 1.0, `search_recency_window_days` sonra
        `search_recency_decay_floor`'a iner). Additive bonus yerine çarpımsal
        decay kullanılır: skor tavanına (1.0) takılan tam eşleşmeler artık
        tazelikten etkilenmeye devam eder, sadece toplama ile maskelenmez.
        Taraflardan biri hata verirse diğeri tek başına sonuç döndürür.

        `query_expander` (opsiyonel) — LLM ile ilişkili ek terimler üretir
        ("İstanbul" → "Beykoz"). SADECE keyword tarafına, düşük ağırlıkla
        (`_EXPANSION_WEIGHT`) eklenir; semantik taraf hiç etkilenmez (embedding
        sorgusunu genişletilmiş terimlerle şişirmek orijinal sorgunun anlamını
        sulandırma riski taşır). Genişletme başarısız olursa (exception/boş
        liste) arama sessizce orijinal sorguyla devam eder — bkz. spec
        "arama ilişkisel genişletme" (20 Ağu 2026).
        """
        candidate_size = min(max(n_results * _CANDIDATE_MULTIPLIER, _MIN_CANDIDATES), _MAX_CANDIDATES)
        query_terms = self._tokenize(query)  # includes Turkish stems for better recall (SQL adayı)
        relevance_terms = self._canonical_terms(query)  # coverage skoru için — bkz. docstring

        expanded_terms: List[str] = []
        if self.query_expander:
            try:
                expanded_terms = self.query_expander.expand(query)
            except Exception as e:
                logger.warning("Sorgu genişletme başarısız, orijinal sorguyla devam: %s", e)

        # Genişletilmiş terimler SQL aday havuzuna da girer — yoksa o makale
        # DB'den hiç çekilmez, _keyword_relevance onu hiç göremez.
        sql_terms = query_terms + [t.lower() for t in expanded_terms if t]

        semantic_by_id: dict = {}
        if self.search_repository:
            try:
                for r in self.search_repository.search(query, candidate_size, source, sentiment):
                    semantic_by_id[r["id"]] = r
            except Exception as e:
                logger.error(f"Semantik arama hatası: {e}")

        try:
            keyword_articles = self.repository.keyword_search(
                query, candidate_size, source, sentiment, terms=sql_terms
            )
        except Exception as e:
            logger.error(f"Keyword arama hatası: {e}")
            keyword_articles = []
        keyword_by_id: dict = {}
        for article in keyword_articles:
            relevance = self._keyword_relevance(article, relevance_terms, secondary_terms=expanded_terms)
            if relevance > 0:
                keyword_by_id[str(article.id)] = (relevance, article)
```

- [ ] **Step 5: Yeni testleri çalıştırıp geçtiğini doğrula**

Run: `venv\Scripts\python.exe -m pytest tests/application/test_news_service.py -k "expander" -v`
Expected: 3 test PASS.

- [ ] **Step 6: TÜM `test_news_service.py` dosyasını çalıştır (regresyon)**

Run: `venv\Scripts\python.exe -m pytest tests/application/test_news_service.py -v`
Expected: TÜMÜ PASS — özellikle `test_hybrid_search_*` mevcut testlerin
hiçbiri kırılmamış olmalı (query_expander=None varsayılan, eski davranış
korunuyor).

- [ ] **Step 7: Commit**

```bash
git add src/application/services/news_service.py tests/application/test_news_service.py
git commit -m "feat: hybrid_search'e opsiyonel LLM tabanlı sorgu genişletme entegrasyonu"
```

---

### Task 7: `dependencies.py` wiring + tam regresyon + manuel doğrulama

**Files:**
- Modify: `src/dependencies.py:64-68` (`get_news_service`)

**Interfaces:**
- Consumes: `build_query_expander(cache)` (Task 4), `get_cache()`
  (`src/dependencies.py`, zaten var).
- Produces: yok — bu son wiring adımı, hiçbir sonraki task buna bağımlı değil.

- [ ] **Step 1: `get_news_service`'i güncelle**

`src/dependencies.py`'nin üstüne import ekle:

```python
from src.adapters.analysis.factory import build_analyzer, build_query_expander
```

(mevcut `from src.adapters.analysis.factory import build_analyzer` satırını
bununla DEĞİŞTİR, iki ayrı import satırı olmasın.)

`get_news_service` fonksiyonunu şununla değiştir:

```python
def get_news_service(db: Session = Depends(get_db)) -> NewsService:
    repo = NewsRepository(db)
    analyzer = build_analyzer()
    search_repo = get_search_repository()
    query_expander = build_query_expander(get_cache())
    return NewsService(
        repository=repo, analyzer=analyzer,
        search_repository=search_repo, query_expander=query_expander,
    )
```

- [ ] **Step 2: Import'un çalıştığını doğrula**

Run: `venv\Scripts\python.exe -c "from src.dependencies import get_news_service; print('ok')"`
Expected: `ok` yazdırır, hata yok (dolaylı olarak `src.main`'in import
zincirini de kırmadığını doğrular).

- [ ] **Step 3: TAM test paketini çalıştır**

Run: `venv\Scripts\python.exe -m pytest tests/ -v`
Expected: TÜMÜ PASS (mevcut ~692 test + bu plandaki ~22 yeni test).

- [ ] **Step 4: Frontend'e dokunulmadığını doğrula (opsiyonel ama ucuz)**

Bu plan sadece backend değiştiriyor, frontend build'e gerek yok — atlanabilir.

- [ ] **Step 5: Commit**

```bash
git add src/dependencies.py
git commit -m "feat: get_news_service artık query_expander'ı DI ile bağlıyor"
```

- [ ] **Step 6: CLAUDE.md'yi güncelle**

`CLAUDE.md`'deki "v1.11 sonrası yeni env var'lar" listesine
`SEARCH_QUERY_EXPANSION_ENABLED` (varsayılan `true`) ekle; "MEVCUT DURUM"
bölümündeki test sayısını güncel toplam ile değiştir; YOL HARİTASI'na bu
işin tamamlandığını (✅) not düş, spec dosyasının yoluna referans ver.

```bash
git add CLAUDE.md
git commit -m "docs: CLAUDE.md'ye sorgu genişletme env var'ı + roadmap güncellemesi"
```

---

## Uygulama Sonrası Manuel Doğrulama (opsiyonel, prod'a çıkmadan önce)

Bu adımlar otomatik test DEĞİL, gerçek Groq'a gitmeden önce bir sağlık
kontrolü — plan tamamlandıktan sonra, deploy kararı verilmeden önce
kullanıcıyla birlikte yapılabilir:

1. Local'de `SEARCH_QUERY_EXPANSION_ENABLED=true` ile `docker compose up -d`,
   `/news/search` ile "istanbul" ara, sonuçlarda "Beykoz" gibi ilçe geçen
   bir haberin (varsa) düşük ama sıfırdan farklı bir skorla göründüğünü
   doğrula.
2. `SEARCH_QUERY_EXPANSION_ENABLED=false` yapıp aynı aramayı tekrarla,
   sonuçların ESKİ (genişletmesiz) haliyle birebir aynı olduğunu doğrula.
3. Groq kotasını (bkz. CLAUDE.md "Local ve prod AYNI paylaşılan
   GROQ_API_KEY'i kullanıyor" notu) tüketmemek için bu testi KISA tut ve
   hemen ardından `docker compose down`.
