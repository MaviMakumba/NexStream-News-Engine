# RAG Tam Metin (soru anında makale çekme) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** "Soru Sor" (RAG) kanıt paketindeki en iyi 2 haberin tam metnini soru anında çekip, soruyla en alakalı pasajları LLM'e vermek.

**Architecture:** Hexagonal. Domain'de `ArticleTextPort` + saf pasaj seçimi; adapter'larda HTTP çekici (SSRF korumalı), HTML çıkarıcı ve cache decorator'ı; application'da `EvidenceEnricher`. `NewsService.answer_question` yalnızca tek bir fail-open "zenginleştir" çağrısı ekler. Metin DB'ye yazılmaz, yalnız kısa TTL'li cache'te yaşar.

**Tech Stack:** Python 3.13, FastAPI (sync handler, threadpool), httpx 0.28 (sync `Client` + `MockTransport` testleri), beautifulsoup4 + lxml (zaten `requirements.txt`'te), `EmbeddingPort`/`CachePort`, prometheus_client, pytest.

**Spec:** `docs/superpowers/specs/2026-10-07-rag-tam-metin-design.md`

## Global Constraints

- Tam makale metni DB'ye YAZILMAZ; yalnız `CachePort` (Redis, başarı 1 saat, başarısızlık 5 dk).
- `src/infrastructure/*` hiçbir `src/adapters/*` import etmez; domain katmanı dış bağımlılık (bs4, httpx, redis) import etmez.
- Her adım fail-open: çekme/çıkarma/embedding hatası → o haber eski `content[:500]` ile devam eder, kullanıcı hata görmez.
- Haber başına zaman 4 sn, toplam 6 sn; gövde en fazla 1_500_000 bayt; yalnız `text/html`; en çok 3 yönlendirme.
- SSRF: yalnız http/https, port 80/443, çözülen HER IP ve HER yönlendirme sonrası `ipaddress.is_global` olmalı.
- Token hedefi: haber başına `rag_passage_token_budget=450`, `rag_fetch_top_n=2`.
- Testlerde gerçek ağ yok; `httpx.MockTransport` ve sahte port'lar kullanılır.
- Yeni modüller `requirements-light.txt`'te (scheduler) olmayan paketleri import eder ama scheduler/embedder bunları import etmez (bkz. `tests/infrastructure/test_embedder_image_closure.py`, `test_logger_no_web_deps.py` yeşil kalmalı).
- Prometheus metrikleri `nexstream_` önekli; etiket kümesi sabit (`result` ∈ hit|fetched|failed|blocked|too_short) — kaynak/host etiketi YOK (Hacker News gibi kaynaklar keyfi sitelere link verir, kardinalite sınırsız olur).
- Branch: `feat/rag-full-text-evidence` (main'e commit YOK). PR merge'i prod deploy tetikler; kullanıcı onayı olmadan merge edilmez.

## Review Focus

Spec'in söylemediği ama kullanıcıya zarar verebilecek girdi sınıfları (her birinin testi ilgili task'ta):

1. **Makale metninde `"` ve satır sonu** — RAG prompt'u `Content: "..."` biçiminde tırnaklı; tırnaklı/çok satırlı metin prompt'u bozar ve prompt-injection yüzeyidir → metin tek satıra düzleştirilir, `"` → `'` (Task 7).
2. **Yavaş damlatan / dev gövde** — sunucu veriyi saniyede birkaç bayt gönderir ya da 3 MB döner → bayt tavanı + süre sınırı (Task 5).
3. **Yönlendirmeyle iç ağa kaçış, `file://`, IPv4-mapped IPv6 (`::ffff:127.0.0.1`), 80/443 dışı port** (Task 4, Task 5).
4. **`<article>` etiketi olmayan sayfa ve HTML olmayan içerik (PDF)** (Task 3, Task 5).
5. **Kaynak engelliyorsa her soruda yeniden denenmesi** — başarısızlık da cache'lenmeli (Task 6); **embedder'ın düşük olması** → teaser'a düşüş (Task 7).

---

## File Structure

| Dosya | Sorumluluk |
|---|---|
| `src/domain/ports/article_text_port.py` (yeni) | `ArticleTextPort.fetch(url) -> Optional[str]` sözleşmesi |
| `src/domain/services/passage_selection.py` (yeni) | Saf: paragraf bölme, token tahmini, kosinüs, pasaj seçimi |
| `src/adapters/scrapers/http_identity.py` (yeni) | Paylaşılan `BROWSER_USER_AGENT` sabiti |
| `src/adapters/scrapers/article_extractor.py` (yeni) | Saf: HTML → paragraflar (bs4+lxml) |
| `src/adapters/scrapers/url_safety.py` (yeni) | `assert_public_http_url`, `UnsafeUrlError` |
| `src/adapters/scrapers/article_text_fetcher.py` (yeni) | `HttpArticleTextFetcher` |
| `src/adapters/scrapers/caching_article_text_fetcher.py` (yeni) | `CachingArticleTextFetcher` decorator |
| `src/adapters/scrapers/article_text_factory.py` (yeni) | `build_evidence_enricher(cache, embedder)` kompozisyon |
| `src/application/services/evidence_enricher.py` (yeni) | `EvidenceEnricher` |
| `src/adapters/api/metrics.py` (değişir) | `article_fetch_total`, `article_fetch_seconds` |
| `src/infrastructure/config/settings.py` (değişir) | `rag_fetch_*` ayarları |
| `src/adapters/scrapers/rss_scrapers.py` (değişir) | `_USER_AGENT = BROWSER_USER_AGENT` |
| `src/application/services/news_service.py` (değişir) | `evidence_enricher` parametresi + `_enrich_evidence` |
| `src/dependencies.py` (değişir) | `get_evidence_enricher()` + `get_news_service` bağlantısı |

Testler: `tests/domain/test_passage_selection.py`, `tests/adapters/test_article_extractor.py`, `test_url_safety.py`, `test_article_text_fetcher.py`, `test_caching_article_text_fetcher.py`, `test_article_text_factory.py`, `tests/application/test_evidence_enricher.py`, `tests/application/test_news_service.py` (ek), `tests/infrastructure/test_rag_fetch_settings.py`.

Test komutu (repo kökünden, PowerShell): `venv\Scripts\python.exe -m pytest <yol> -v`

---

### Task 1: Ayarlar, metrikler, paylaşılan User-Agent

**Files:**
- Modify: `src/infrastructure/config/settings.py` (satır ~229, `rag_retrieval_threshold`'dan sonra)
- Modify: `src/adapters/api/metrics.py` (dosya sonuna)
- Create: `src/adapters/scrapers/http_identity.py`
- Modify: `src/adapters/scrapers/rss_scrapers.py:51-54`
- Test: `tests/infrastructure/test_rag_fetch_settings.py`, `tests/adapters/test_rss_scrapers.py` (mevcut UA testi koruma görevi görür)

**Interfaces:**
- Produces: `settings.rag_fetch_enabled: bool`, `rag_fetch_top_n: int`, `rag_passage_token_budget: int`, `rag_fetch_timeout_seconds: float`, `rag_fetch_total_timeout_seconds: float`, `rag_fetch_cache_ttl_seconds: int`, `rag_fetch_failure_ttl_seconds: int`, `rag_fetch_max_bytes: int`; `metrics.article_fetch_total` (Counter, label `result`), `metrics.article_fetch_seconds` (Histogram); `http_identity.BROWSER_USER_AGENT: str`.

- [ ] **Step 1: Write the failing test**

`tests/infrastructure/test_rag_fetch_settings.py`:

```python
from src.infrastructure.config.settings import Settings


def test_rag_fetch_defaults_match_spec():
    s = Settings()
    assert s.rag_fetch_enabled is True
    assert s.rag_fetch_top_n == 2
    assert s.rag_passage_token_budget == 450
    assert s.rag_fetch_timeout_seconds == 4.0
    assert s.rag_fetch_total_timeout_seconds == 6.0
    assert s.rag_fetch_cache_ttl_seconds == 3600
    assert s.rag_fetch_failure_ttl_seconds == 300
    assert s.rag_fetch_max_bytes == 1_500_000


def test_article_fetch_metrics_are_registered_with_fixed_labels():
    from src.adapters.api.metrics import article_fetch_total, article_fetch_seconds
    for result in ("hit", "fetched", "failed", "blocked", "too_short"):
        article_fetch_total.labels(result=result).inc(0)
    assert article_fetch_seconds is not None


def test_rss_scraper_and_fetcher_share_one_user_agent():
    from src.adapters.scrapers.http_identity import BROWSER_USER_AGENT
    from src.adapters.scrapers.rss_scrapers import BaseRssScraper
    assert BaseRssScraper._USER_AGENT == BROWSER_USER_AGENT
    assert BROWSER_USER_AGENT.startswith("Mozilla/5.0 (") and "Chrome/" in BROWSER_USER_AGENT
```

- [ ] **Step 2: Run test to verify it fails**

Run: `venv\Scripts\python.exe -m pytest tests/infrastructure/test_rag_fetch_settings.py -v`
Expected: FAIL (`AttributeError`/`ImportError`).

- [ ] **Step 3: Write minimal implementation**

`settings.py` — `rag_retrieval_threshold: float = 0.4` satırından hemen sonra ekle:

```python
    # RAG tam metin zenginleştirmesi (7 Eki 2026, spec 2026-10-07-rag-tam-metin-design.md).
    # Kanıt paketindeki en iyi `rag_fetch_top_n` haberin makale gövdesi soru anında çekilir,
    # soruyla en alakalı pasajlar (haber başına `rag_passage_token_budget` token) LLM'e verilir.
    # 120b'de RAG payı ~50K token/gün: ham tam metin günde ~10 soruya mal olurdu, o yüzden pasaj
    # seçimi şart. Metin DB'ye YAZILMAZ (telif kararı), yalnız kısa TTL'li cache'te yaşar.
    rag_fetch_enabled: bool = True                 # kapatma anahtarı (RAG_FETCH_ENABLED=false)
    rag_fetch_top_n: int = 2
    rag_passage_token_budget: int = 450            # haber başına
    rag_fetch_timeout_seconds: float = 4.0         # haber başına
    rag_fetch_total_timeout_seconds: float = 6.0   # soru başına toplam
    rag_fetch_cache_ttl_seconds: int = 3600
    rag_fetch_failure_ttl_seconds: int = 300       # engelleyen kaynak her soruda yeniden denenmesin
    rag_fetch_max_bytes: int = 1_500_000
```

`src/adapters/scrapers/http_identity.py`:

```python
"""Dış sitelere giden tüm HTTP istemcilerinin paylaştığı tarayıcı kimliği.

Bare "Mozilla/5.0" klasik bot imzasıdır — gerçek tarayıcılar hiçbir zaman tek başına
göndermez; AA'nın WAF'ı bunu TLS seviyesinde reddediyordu (9 Eylül 2026). RSS çekicisi ve
makale metni çekicisi AYNI sabiti kullanır ki UA bir yerde güncellenip ötekinde unutulmasın.
"""

BROWSER_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
)
```

`rss_scrapers.py` — mevcut 4 satırlık `_USER_AGENT = (...)` tanımını şununla değiştir (yorum bloğu kalsın), dosya başına import ekle:

```python
from src.adapters.scrapers.http_identity import BROWSER_USER_AGENT
...
    _USER_AGENT = BROWSER_USER_AGENT
```

`metrics.py` sonuna:

```python
# 7 Eki 2026 — RAG tam metin çekme (spec 2026-10-07-rag-tam-metin-design.md). `result`:
# hit (cache) / fetched / failed (ağ, HTTP, ayrıştırma) / blocked (SSRF koruması ya da kaynak
# 401/403/429 ile reddetti) / too_short (çıkarılan metin kullanılamayacak kadar kısa).
# Host etiketi KASITLI yok: Hacker News gibi kaynaklar keyfi sitelere link verir (sınırsız
# kardinalite). Kaynak bazlı bakış için `failed`/`blocked` loglarındaki host'a (Loki) bak.
article_fetch_total = Counter(
    "nexstream_article_fetch_total",
    "Article full-text fetch attempts by result",
    ["result"],
)
article_fetch_seconds = Histogram(
    "nexstream_article_fetch_seconds",
    "Article full-text fetch duration in seconds",
    buckets=[0.25, 0.5, 1.0, 2.0, 3.0, 4.0, 6.0],
)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `venv\Scripts\python.exe -m pytest tests/infrastructure/test_rag_fetch_settings.py tests/adapters/test_rss_scrapers.py tests/adapters/test_prometheus_metrics.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/infrastructure/config/settings.py src/adapters/api/metrics.py src/adapters/scrapers/http_identity.py src/adapters/scrapers/rss_scrapers.py tests/infrastructure/test_rag_fetch_settings.py
git commit -m 'feat(rag): tam metin ayarlari, metrikleri ve paylasilan UA sabiti'
```

---

### Task 2: Domain — `ArticleTextPort` ve saf pasaj seçimi

**Files:**
- Create: `src/domain/ports/article_text_port.py`
- Create: `src/domain/services/passage_selection.py`
- Test: `tests/domain/test_passage_selection.py`

**Interfaces:**
- Produces:
  - `ArticleTextPort.fetch(self, url: str) -> Optional[str]` (abstract; asla fırlatmaz)
  - `split_paragraphs(text: str) -> list[str]`
  - `estimate_tokens(text: str) -> int`
  - `cosine_similarity(a: Sequence[float], b: Sequence[float]) -> float`
  - `select_passages(paragraphs: Sequence[str], question_vector: Sequence[float], paragraph_vectors: Sequence[Sequence[float]], token_budget: int) -> list[str]` (özgün sırada döner)

- [ ] **Step 1: Write the failing test**

`tests/domain/test_passage_selection.py`:

```python
import pytest

from src.domain.services.passage_selection import (
    MAX_PARAGRAPHS,
    MAX_PARAGRAPH_CHARS,
    cosine_similarity,
    estimate_tokens,
    select_passages,
    split_paragraphs,
)

P1 = "Birinci paragraf, yeterince uzun bir cümleden oluşuyor ve filtreyi geçer."
P2 = "İkinci paragraf, oyuncunun sakatlığı hakkında kulüp doktorunun açıklamasını içerir."
P3 = "Üçüncü paragraf, bilet fiyatları ve stat doluluğu hakkında alakasız bilgi verir."


def test_split_paragraphs_drops_short_lines_and_collapses_whitespace():
    text = f"Kısa\n\n{P1}\n   \n  {P2.replace(' ', '   ')}  \n"
    assert split_paragraphs(text) == [P1, P2]


def test_split_paragraphs_truncates_long_paragraph_and_caps_count():
    long = "a" * (MAX_PARAGRAPH_CHARS + 500)
    assert split_paragraphs(long) == ["a" * MAX_PARAGRAPH_CHARS]
    many = "\n".join(f"{P1} {i}" for i in range(MAX_PARAGRAPHS + 20))
    assert len(split_paragraphs(many)) == MAX_PARAGRAPHS


def test_split_paragraphs_empty_text():
    assert split_paragraphs("") == []


def test_estimate_tokens_is_conservative_ceiling():
    assert estimate_tokens("") == 0
    assert estimate_tokens("abc") == 1
    assert estimate_tokens("abcd") == 2


def test_cosine_similarity_basic_and_zero_vector():
    assert cosine_similarity([1, 0], [1, 0]) == pytest.approx(1.0)
    assert cosine_similarity([1, 0], [0, 1]) == pytest.approx(0.0)
    assert cosine_similarity([0, 0], [1, 0]) == 0.0


def test_select_passages_picks_most_similar_within_budget_in_original_order():
    paragraphs = [P1, P2, P3]
    vectors = [[0, 1], [1, 0], [0.7, 0.7]]
    # her paragraf ~25 token; bütçe 55 -> yalnız en benzer ikisi (P2, P3) sığar
    chosen = select_passages(paragraphs, [1, 0], vectors, token_budget=55)
    assert chosen == [P2, P3]


def test_select_passages_skips_paragraph_that_does_not_fit_but_keeps_looking():
    big = "x" * 300  # ~100 token
    chosen = select_passages([big, P2], [1, 0], [[1, 0], [0.5, 0.5]], token_budget=40)
    assert chosen == [P2]


def test_select_passages_truncates_best_when_nothing_fits_budget():
    big = "y" * 300
    chosen = select_passages([big], [1, 0], [[1, 0]], token_budget=10)
    assert len(chosen) == 1 and len(chosen[0]) == 10 * 3


def test_select_passages_empty_and_mismatched_inputs():
    assert select_passages([], [1, 0], [], token_budget=100) == []
    with pytest.raises(ValueError):
        select_passages([P1, P2], [1, 0], [[1, 0]], token_budget=100)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `venv\Scripts\python.exe -m pytest tests/domain/test_passage_selection.py -v`
Expected: FAIL (`ModuleNotFoundError`).

- [ ] **Step 3: Write minimal implementation**

`src/domain/ports/article_text_port.py`:

```python
"""ArticleTextPort — bir haber URL'sinden temiz makale metni getirme sözleşmesi.

`NewsScraperPort` (RSS listesi) ile KARIŞTIRILMAMALI: o haber LİSTESİ üretir, bu tek bir
haberin gövde metnini soru anında getirir (RAG, spec 2026-10-07-rag-tam-metin-design.md).
"""

from abc import ABC, abstractmethod
from typing import Optional


class ArticleTextPort(ABC):
    @abstractmethod
    def fetch(self, url: str) -> Optional[str]:
        """Makale gövde metnini döner; paywall/engel/timeout/boş sonuç dahil HER başarısızlıkta
        `None`. ASLA exception fırlatmaz (çağıran fail-open'dır)."""
```

`src/domain/services/passage_selection.py`:

```python
"""Saf pasaj seçimi — makale metninden soruya en alakalı paragrafları token bütçesi içinde seçer.

Embedding çağrısı burada YOK (domain dış bağımlılık bilmez): vektörler dışarıdan gelir,
`EvidenceEnricher` `EmbeddingPort` ile üretir.
"""

import math
import re
from typing import Sequence

MIN_PARAGRAPH_CHARS = 40
MAX_PARAGRAPH_CHARS = 600
MAX_PARAGRAPHS = 60
# Türkçe için muhafazakâr (gerçek oran ~3.5-4 karakter/token): bütçeyi aşmaktansa az doldurmak.
CHARS_PER_TOKEN = 3


def estimate_tokens(text: str) -> int:
    return (len(text) + CHARS_PER_TOKEN - 1) // CHARS_PER_TOKEN


def split_paragraphs(text: str) -> list[str]:
    paragraphs: list[str] = []
    for raw in re.split(r"\n+", text):
        paragraph = " ".join(raw.split())
        if len(paragraph) < MIN_PARAGRAPH_CHARS:
            continue
        paragraphs.append(paragraph[:MAX_PARAGRAPH_CHARS])
        if len(paragraphs) >= MAX_PARAGRAPHS:
            break
    return paragraphs


def cosine_similarity(a: Sequence[float], b: Sequence[float]) -> float:
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return sum(x * y for x, y in zip(a, b)) / (norm_a * norm_b)


def select_passages(
    paragraphs: Sequence[str],
    question_vector: Sequence[float],
    paragraph_vectors: Sequence[Sequence[float]],
    token_budget: int,
) -> list[str]:
    """Soruya en benzer paragrafları açgözlü seçer; sığmayanı atlayıp aramaya devam eder.
    Hiçbiri sığmazsa en iyisi bütçeye kırpılır. Dönüş özgün metin sırasındadır."""
    if len(paragraphs) != len(paragraph_vectors):
        raise ValueError("paragraphs ve paragraph_vectors aynı uzunlukta olmalı")
    if not paragraphs:
        return []
    ranked = sorted(
        range(len(paragraphs)),
        key=lambda i: cosine_similarity(question_vector, paragraph_vectors[i]),
        reverse=True,
    )
    chosen: list[int] = []
    used = 0
    for i in ranked:
        cost = estimate_tokens(paragraphs[i])
        if used + cost > token_budget:
            continue
        chosen.append(i)
        used += cost
    if not chosen:
        return [paragraphs[ranked[0]][: token_budget * CHARS_PER_TOKEN]]
    return [paragraphs[i] for i in sorted(chosen)]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `venv\Scripts\python.exe -m pytest tests/domain/test_passage_selection.py -v`
Expected: PASS (9 test).

- [ ] **Step 5: Commit**

```bash
git add src/domain/ports/article_text_port.py src/domain/services/passage_selection.py tests/domain/test_passage_selection.py
git commit -m 'feat(rag): ArticleTextPort ve saf pasaj secimi'
```

---

### Task 3: HTML makale çıkarıcı

**Files:**
- Create: `src/adapters/scrapers/article_extractor.py`
- Test: `tests/adapters/test_article_extractor.py`

**Interfaces:**
- Produces: `extract_article_text(html: bytes | str) -> str` — paragrafları `"\n\n"` ile birleştirilmiş metin; bulunamazsa `""`.

- [ ] **Step 1: Write the failing test**

`tests/adapters/test_article_extractor.py`:

```python
from src.adapters.scrapers.article_extractor import extract_article_text

BODY_1 = "Kulüp doktoru oyuncunun sağ ayak bileğindeki sakatlığın ciddi olduğunu açıkladı."
BODY_2 = "Yıldız oyuncunun yaklaşık üç hafta sahalardan uzak kalması bekleniyor, tedavi sürüyor."


def test_extracts_article_paragraphs_and_drops_nav_script_footer():
    html = f"""<html><head><meta charset="utf-8"><title>x</title><script>var a = 1;</script></head>
    <body><nav><p>Anasayfa Spor Ekonomi Dünya Magazin Gündem Yaşam</p></nav>
    <article><h1>Başlık</h1><p>{BODY_1}</p><p>{BODY_2}</p></article>
    <footer><p>Tüm hakları saklıdır. Çerez politikası ve gizlilik bildirimi için tıklayın.</p></footer>
    </body></html>"""
    text = extract_article_text(html)
    assert text == f"{BODY_1}\n\n{BODY_2}"


def test_without_article_tag_picks_densest_paragraph_group():
    html = f"""<html><body>
    <div class="story"><p>{BODY_1}</p><p>{BODY_2}</p></div>
    <div class="related"><p>Kısa ilgili haber başlığı bir cümle daha uzun yapıldı şimdi tamam.</p></div>
    </body></html>"""
    text = extract_article_text(html)
    assert BODY_1 in text and BODY_2 in text
    assert "ilgili haber" not in text


def test_short_paragraphs_are_ignored():
    html = f"<html><body><article><p>Paylaş</p><p>{BODY_1}</p><p>Yorum yap</p></article></body></html>"
    assert extract_article_text(html) == BODY_1


def test_accepts_bytes_with_turkish_characters():
    html = f'<html><head><meta charset="utf-8"></head><body><article><p>{BODY_1}</p></article></body></html>'
    assert extract_article_text(html.encode("utf-8")) == BODY_1


def test_empty_or_paragraphless_html_returns_empty_string():
    assert extract_article_text("") == ""
    assert extract_article_text("<html><body><div>sadece div</div></body></html>") == ""
```

- [ ] **Step 2: Run test to verify it fails**

Run: `venv\Scripts\python.exe -m pytest tests/adapters/test_article_extractor.py -v`
Expected: FAIL (`ModuleNotFoundError`).

- [ ] **Step 3: Write minimal implementation**

`src/adapters/scrapers/article_extractor.py`:

```python
"""HTML → makale paragrafları. Kaynak başına özel kural YOK: genel bir paragraf-yoğunluğu
sezgisi (`<article>` varsa orası, yoksa en çok metin taşıyan paragraf grubu). Çıkmayan
kaynaklar `nexstream_article_fetch_total{result="too_short"}` ile görünür olur ve gerekirse
kaynak bazlı kural AYRI bir işte eklenir (spec: kapsam dışı).
"""

from bs4 import BeautifulSoup

_NOISE_TAGS = ["script", "style", "noscript", "nav", "aside", "footer", "header", "form", "iframe", "figure", "svg"]
_MIN_PARAGRAPH_CHARS = 40
_MIN_ARTICLE_SCOPE_CHARS = 200


def _clean(tag) -> str:
    return " ".join(tag.get_text(" ", strip=True).split())


def extract_article_text(html) -> str:
    soup = BeautifulSoup(html, "lxml")
    for tag in soup(_NOISE_TAGS):
        tag.decompose()

    scope = soup.find("article")
    paragraphs = scope.find_all("p") if scope else []
    if sum(len(_clean(p)) for p in paragraphs) < _MIN_ARTICLE_SCOPE_CHARS:
        paragraphs = soup.find_all("p")

    groups: dict[int, list[str]] = {}
    for p in paragraphs:
        text = _clean(p)
        if len(text) < _MIN_PARAGRAPH_CHARS:
            continue
        groups.setdefault(id(p.parent), []).append(text)
    if not groups:
        return ""
    best = max(groups.values(), key=lambda texts: sum(len(t) for t in texts))
    return "\n\n".join(best)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `venv\Scripts\python.exe -m pytest tests/adapters/test_article_extractor.py -v`
Expected: PASS (5 test). Not: ilk testte `<article>` kapsamı (iki paragraf ~170 karakter) 200'ün altında kalırsa `soup.find_all("p")` yoluna düşer ve yine tek grup (article) en yoğundur — sonuç aynı kalır; yine de test PASS vermiyorsa `BODY_1/BODY_2` uzunluklarını kontrol et.

- [ ] **Step 5: Commit**

```bash
git add src/adapters/scrapers/article_extractor.py tests/adapters/test_article_extractor.py
git commit -m 'feat(rag): genel HTML makale cikarici'
```

---

### Task 4: SSRF URL koruması

**Files:**
- Create: `src/adapters/scrapers/url_safety.py`
- Test: `tests/adapters/test_url_safety.py`

**Interfaces:**
- Produces: `UnsafeUrlError(ValueError)`; `assert_public_http_url(url: str, resolver=socket.getaddrinfo) -> None` — güvensizse `UnsafeUrlError` fırlatır. `resolver(host, port, type=socket.SOCK_STREAM)` `getaddrinfo` biçiminde `[(family, type, proto, canonname, (ip, port, ...))]` döner.

- [ ] **Step 1: Write the failing test**

`tests/adapters/test_url_safety.py`:

```python
import socket

import pytest

from src.adapters.scrapers.url_safety import UnsafeUrlError, assert_public_http_url


def _resolver(*ips):
    def resolve(host, port, type=socket.SOCK_STREAM):
        return [(socket.AF_INET, type, 6, "", (ip, port)) for ip in ips]
    return resolve


def test_public_https_url_passes():
    assert_public_http_url("https://example.com/haber/1", resolver=_resolver("93.184.216.34"))


@pytest.mark.parametrize("url", [
    "file:///etc/passwd",
    "ftp://example.com/x",
    "gopher://example.com/",
    "javascript:alert(1)",
    "//example.com/x",
    "https:///nohost",
])
def test_non_http_or_hostless_urls_rejected(url):
    with pytest.raises(UnsafeUrlError):
        assert_public_http_url(url, resolver=_resolver("93.184.216.34"))


@pytest.mark.parametrize("ip", [
    "127.0.0.1", "10.0.0.5", "172.16.3.4", "192.168.1.1",
    "169.254.169.254", "100.64.0.1", "0.0.0.0", "::1", "fe80::1", "::ffff:127.0.0.1", "fc00::1",
])
def test_non_global_addresses_rejected(ip):
    with pytest.raises(UnsafeUrlError):
        assert_public_http_url("https://evil.example/x", resolver=_resolver(ip))


def test_rejected_if_any_resolved_address_is_private():
    with pytest.raises(UnsafeUrlError):
        assert_public_http_url("https://mixed.example/", resolver=_resolver("93.184.216.34", "10.0.0.1"))


def test_unresolvable_host_and_empty_resolution_rejected():
    def boom(host, port, type=socket.SOCK_STREAM):
        raise socket.gaierror("nope")
    with pytest.raises(UnsafeUrlError):
        assert_public_http_url("https://nxdomain.example/", resolver=boom)
    with pytest.raises(UnsafeUrlError):
        assert_public_http_url("https://empty.example/", resolver=lambda h, p, type=0: [])


@pytest.mark.parametrize("url", ["https://example.com:8080/x", "http://example.com:22/"])
def test_non_web_ports_rejected(url):
    with pytest.raises(UnsafeUrlError):
        assert_public_http_url(url, resolver=_resolver("93.184.216.34"))


def test_explicit_standard_ports_allowed():
    assert_public_http_url("http://example.com:80/x", resolver=_resolver("93.184.216.34"))
    assert_public_http_url("https://example.com:443/x", resolver=_resolver("93.184.216.34"))
```

- [ ] **Step 2: Run test to verify it fails**

Run: `venv\Scripts\python.exe -m pytest tests/adapters/test_url_safety.py -v`
Expected: FAIL (`ModuleNotFoundError`).

- [ ] **Step 3: Write minimal implementation**

`src/adapters/scrapers/url_safety.py`:

```python
"""SSRF koruması — makale URL'leri kendi RSS'imizden gelir ama kötü niyetli/ele geçirilmiş bir
feed (ya da Hacker News gibi keyfi sitelere link veren bir kaynak) iç ağı hedefleyemesin.

Bilinen sınır: DNS çözümü ile gerçek bağlantı arasında TOCTOU (DNS rebinding) penceresi var;
HTTPS'te IP'ye sabitlemek SNI/sertifika doğrulamasını karmaşıklaştırdığı için ilk sürümde
kabul edildi. Çıkış yalnız GET + yalnız HTML okuma + cevap kullanıcıya ham dönmediği için
etkisi sınırlı (metin yalnız LLM bağlamına girer).
"""

import ipaddress
import socket
from urllib.parse import urlsplit

_ALLOWED_PORTS = {80, 443}


class UnsafeUrlError(ValueError):
    """URL fetch edilmemeli (şema, port ya da çözülen adres güvensiz)."""


def assert_public_http_url(url: str, resolver=socket.getaddrinfo) -> None:
    parts = urlsplit(url)
    if parts.scheme not in ("http", "https"):
        raise UnsafeUrlError(f"izin verilmeyen şema: {parts.scheme!r}")
    host = parts.hostname
    if not host:
        raise UnsafeUrlError("host yok")
    try:
        port = parts.port or (443 if parts.scheme == "https" else 80)
    except ValueError as e:
        raise UnsafeUrlError("geçersiz port") from e
    if port not in _ALLOWED_PORTS:
        raise UnsafeUrlError(f"izin verilmeyen port: {port}")
    try:
        infos = resolver(host, port, type=socket.SOCK_STREAM)
    except socket.gaierror as e:
        raise UnsafeUrlError(f"DNS çözülemedi: {host}") from e
    if not infos:
        raise UnsafeUrlError(f"adres bulunamadı: {host}")
    for info in infos:
        ip = ipaddress.ip_address(info[4][0].split("%")[0])
        if ip.version == 6 and ip.ipv4_mapped is not None:
            ip = ip.ipv4_mapped
        if not ip.is_global:
            raise UnsafeUrlError(f"global olmayan adres: {ip}")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `venv\Scripts\python.exe -m pytest tests/adapters/test_url_safety.py -v`
Expected: PASS. (`https:///nohost` ve `//example.com/x` için `hostname`/`scheme` boş kalır → reddedilir.)

- [ ] **Step 5: Commit**

```bash
git add src/adapters/scrapers/url_safety.py tests/adapters/test_url_safety.py
git commit -m 'feat(rag): SSRF URL korumasi'
```

---

### Task 5: `HttpArticleTextFetcher`

**Files:**
- Create: `src/adapters/scrapers/article_text_fetcher.py`
- Test: `tests/adapters/test_article_text_fetcher.py`

**Interfaces:**
- Consumes: `extract_article_text` (Task 3), `assert_public_http_url`/`UnsafeUrlError` (Task 4), `BROWSER_USER_AGENT`, `article_fetch_total`/`article_fetch_seconds` (Task 1), `ArticleTextPort` (Task 2).
- Produces: `HttpArticleTextFetcher(timeout_seconds: float, max_bytes: int, min_chars: int = 200, transport: httpx.BaseTransport | None = None, guard=assert_public_http_url, clock=time.monotonic)`; `.fetch(url) -> Optional[str]`.

- [ ] **Step 1: Write the failing test**

`tests/adapters/test_article_text_fetcher.py`:

```python
import httpx

from src.adapters.api.metrics import article_fetch_total
from src.adapters.scrapers.article_text_fetcher import HttpArticleTextFetcher
from src.adapters.scrapers.http_identity import BROWSER_USER_AGENT
from src.adapters.scrapers.url_safety import UnsafeUrlError

P1 = "Kulüp doktoru oyuncunun sağ ayak bileğindeki sakatlığın ciddi olduğunu açıkladı bugün."
P2 = "Yıldız oyuncunun yaklaşık üç hafta sahalardan uzak kalması bekleniyor, tedavi sürüyor."
P3 = "Teknik direktör, takımın hafta sonu oynanacak derbiye eksik gireceğini söyledi."
PAGE = f"<html><head><meta charset='utf-8'></head><body><article><p>{P1}</p><p>{P2}</p><p>{P3}</p></article></body></html>"
HTML = {"content-type": "text/html; charset=utf-8"}


def _fetcher(handler, **kw):
    kw.setdefault("timeout_seconds", 4.0)
    kw.setdefault("max_bytes", 1_500_000)
    kw.setdefault("guard", lambda url: None)
    return HttpArticleTextFetcher(transport=httpx.MockTransport(handler), **kw)


def _count(result):
    return article_fetch_total.labels(result=result)._value.get()


def test_fetch_returns_article_text_and_sends_browser_user_agent():
    seen = {}

    def handler(request):
        seen["ua"] = request.headers["user-agent"]
        return httpx.Response(200, headers=HTML, content=PAGE.encode("utf-8"))

    before = _count("fetched")
    text = _fetcher(handler).fetch("https://site.example/haber")
    assert P2 in text and P1 in text
    assert seen["ua"] == BROWSER_USER_AGENT
    assert _count("fetched") == before + 1


def test_non_html_content_type_returns_none():
    before = _count("failed")
    f = _fetcher(lambda r: httpx.Response(200, headers={"content-type": "application/pdf"}, content=b"%PDF-1.7"))
    assert f.fetch("https://site.example/x.pdf") is None
    assert _count("failed") == before + 1


def test_source_refusal_counts_as_blocked():
    before = _count("blocked")
    f = _fetcher(lambda r: httpx.Response(403, headers=HTML, content=b"denied"))
    assert f.fetch("https://waf.example/x") is None
    assert _count("blocked") == before + 1


def test_server_error_counts_as_failed():
    before = _count("failed")
    assert _fetcher(lambda r: httpx.Response(500, headers=HTML)).fetch("https://site.example/x") is None
    assert _count("failed") == before + 1


def test_network_error_returns_none():
    def handler(request):
        raise httpx.ConnectError("boom")

    assert _fetcher(handler).fetch("https://down.example/x") is None


def test_too_short_text_returns_none():
    before = _count("too_short")
    html = "<html><body><article><p>Çok kısa ama kırk karakteri aşan tek bir paragraf burada.</p></article></body></html>"
    assert _fetcher(lambda r: httpx.Response(200, headers=HTML, content=html.encode())).fetch("https://s.example/x") is None
    assert _count("too_short") == before + 1


def test_follows_redirects_and_guards_every_hop():
    guarded = []

    def handler(request):
        if request.url.path == "/start":
            return httpx.Response(302, headers={"location": "https://other.example/final"})
        return httpx.Response(200, headers=HTML, content=PAGE.encode("utf-8"))

    f = _fetcher(handler, guard=guarded.append)
    assert P1 in f.fetch("https://site.example/start")
    assert guarded == ["https://site.example/start", "https://other.example/final"]


def test_redirect_to_unsafe_target_is_blocked():
    def guard(url):
        if "internal" in url:
            raise UnsafeUrlError("özel adres")

    def handler(request):
        return httpx.Response(302, headers={"location": "http://internal.local/admin"})

    before = _count("blocked")
    assert _fetcher(handler, guard=guard).fetch("https://site.example/start") is None
    assert _count("blocked") == before + 1


def test_too_many_redirects_returns_none():
    def handler(request):
        return httpx.Response(302, headers={"location": "https://site.example/again"})

    assert _fetcher(handler).fetch("https://site.example/start") is None


def test_body_is_capped_at_max_bytes():
    filler = "<p>" + ("z" * 100) + "</p>"
    html = f"<html><body><article><p>{P1}</p><p>{P2}</p>{filler * 5}<p>SONRAKI_BOLUM_BURADA_BASLIYOR_ve_cok_uzun_devam_ediyor</p></article></body></html>"
    f = _fetcher(lambda r: httpx.Response(200, headers=HTML, content=html.encode("utf-8")), max_bytes=400)
    text = f.fetch("https://site.example/x")
    assert text is not None and "SONRAKI_BOLUM" not in text


class _Chunks(httpx.SyncByteStream):
    def __init__(self, chunks):
        self._chunks = chunks

    def __iter__(self):
        yield from self._chunks


def test_slow_body_is_cut_at_deadline():
    first = f"<html><body><article><p>{P1}</p><p>{P2}</p><p>{P3}</p>".encode("utf-8")
    second = "<p>IKINCI_PARCA_ASLA_OKUNMAMALI_cunku_sure_doldu_tamam_mi_peki</p></article></body></html>".encode("utf-8")
    ticks = {"t": 0.0}

    def clock():
        ticks["t"] += 5.0
        return ticks["t"]

    f = _fetcher(lambda r: httpx.Response(200, headers=HTML, stream=_Chunks([first, second])),
                 timeout_seconds=4.0, clock=clock)
    text = f.fetch("https://slow.example/x")
    assert text is not None and P1 in text and "IKINCI_PARCA" not in text
```

- [ ] **Step 2: Run test to verify it fails**

Run: `venv\Scripts\python.exe -m pytest tests/adapters/test_article_text_fetcher.py -v`
Expected: FAIL (`ModuleNotFoundError`).

- [ ] **Step 3: Write minimal implementation**

`src/adapters/scrapers/article_text_fetcher.py`:

```python
"""HttpArticleTextFetcher — `ArticleTextPort`'un HTTP + HTML çıkarıcı implementasyonu.

Senkron (answer_question senkron bir FastAPI handler'ı; paralellik EvidenceEnricher'ın thread
havuzunda). Yönlendirmeler ELLE izlenir ki her atlamada SSRF kontrolü yapılabilsin.
"""

import logging
import time
from typing import Optional
from urllib.parse import urlsplit

import httpx

from src.adapters.api.metrics import article_fetch_seconds, article_fetch_total
from src.adapters.scrapers.article_extractor import extract_article_text
from src.adapters.scrapers.http_identity import BROWSER_USER_AGENT
from src.adapters.scrapers.url_safety import UnsafeUrlError, assert_public_http_url
from src.domain.ports.article_text_port import ArticleTextPort

logger = logging.getLogger(__name__)

_REFUSAL_STATUSES = {401, 403, 429}


class _SourceRefused(Exception):
    """Kaynak isteği bilerek reddetti (paywall/WAF/rate limit)."""


class HttpArticleTextFetcher(ArticleTextPort):
    _MAX_REDIRECTS = 3

    def __init__(
        self,
        timeout_seconds: float,
        max_bytes: int,
        min_chars: int = 200,
        transport: Optional[httpx.BaseTransport] = None,
        guard=assert_public_http_url,
        clock=time.monotonic,
    ):
        self._timeout = timeout_seconds
        self._max_bytes = max_bytes
        self._min_chars = min_chars
        self._transport = transport
        self._guard = guard
        self._clock = clock

    def fetch(self, url: str) -> Optional[str]:
        started = self._clock()
        result = "failed"
        text: Optional[str] = None
        try:
            extracted = extract_article_text(self._download(url))
            if len(extracted) < self._min_chars:
                result = "too_short"
            else:
                result, text = "fetched", extracted
        except (UnsafeUrlError, _SourceRefused) as e:
            result = "blocked"
            logger.warning("Makale metni engellendi (%s): %s", urlsplit(url).hostname, e)
        except Exception as e:
            logger.warning("Makale metni çekilemedi (%s): %s", urlsplit(url).hostname, e)
        finally:
            article_fetch_total.labels(result=result).inc()
            article_fetch_seconds.observe(self._clock() - started)
        return text

    def _download(self, url: str) -> bytes:
        deadline = self._clock() + self._timeout
        headers = {"User-Agent": BROWSER_USER_AGENT, "Accept": "text/html,application/xhtml+xml"}
        current = url
        with httpx.Client(
            transport=self._transport, timeout=self._timeout, headers=headers, follow_redirects=False
        ) as client:
            for _ in range(self._MAX_REDIRECTS + 1):
                self._guard(current)
                with client.stream("GET", current) as response:
                    if response.is_redirect:
                        location = response.headers.get("location")
                        if not location:
                            raise ValueError("yönlendirme hedefi yok")
                        current = str(httpx.URL(current).join(location))
                        continue
                    if response.status_code in _REFUSAL_STATUSES:
                        raise _SourceRefused(f"HTTP {response.status_code}")
                    response.raise_for_status()
                    content_type = response.headers.get("content-type", "").lower()
                    if "html" not in content_type:
                        raise ValueError(f"beklenmeyen içerik türü: {content_type!r}")
                    return self._read_capped(response, deadline)
        raise ValueError("çok fazla yönlendirme")

    def _read_capped(self, response: httpx.Response, deadline: float) -> bytes:
        chunks: list[bytes] = []
        total = 0
        for chunk in response.iter_bytes():
            chunks.append(chunk)
            total += len(chunk)
            if total >= self._max_bytes or self._clock() > deadline:
                break
        return b"".join(chunks)[: self._max_bytes]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `venv\Scripts\python.exe -m pytest tests/adapters/test_article_text_fetcher.py -v`
Expected: PASS (11 test). `test_slow_body_is_cut_at_deadline`: saat her çağrıda 5 sn ilerler (started=5, deadline=10+4=14, ilk chunk sonrası kontrol 15>14 → kesilir); beklenmedik bir sayıda `clock()` çağrısı eklendiyse `step` ve beklentiyi birlikte gözden geçir.

- [ ] **Step 5: Commit**

```bash
git add src/adapters/scrapers/article_text_fetcher.py tests/adapters/test_article_text_fetcher.py
git commit -m 'feat(rag): SSRF korumali HTTP makale metni cekici'
```

---

### Task 6: `CachingArticleTextFetcher`

**Files:**
- Create: `src/adapters/scrapers/caching_article_text_fetcher.py`
- Test: `tests/adapters/test_caching_article_text_fetcher.py`

**Interfaces:**
- Consumes: `ArticleTextPort`, `CachePort` (`get(key)`, `set(key, value, ttl_seconds)`), `article_fetch_total` (`result="hit"`).
- Produces: `CachingArticleTextFetcher(inner: ArticleTextPort, cache: CachePort, ttl_seconds: int, failure_ttl_seconds: int)`; `.fetch(url)`. Cache anahtarı `"arttext:" + sha1(url)`; başarısızlık `""` olarak saklanır ve `None` döner.

- [ ] **Step 1: Write the failing test**

`tests/adapters/test_caching_article_text_fetcher.py`:

```python
from src.adapters.api.metrics import article_fetch_total
from src.adapters.scrapers.caching_article_text_fetcher import CachingArticleTextFetcher
from src.domain.ports.article_text_port import ArticleTextPort
from src.domain.ports.cache_port import CachePort


class FakeCache(CachePort):
    def __init__(self):
        self.store, self.ttls = {}, {}

    def get(self, key):
        return self.store.get(key)

    def set(self, key, value, ttl_seconds=60):
        self.store[key] = value
        self.ttls[key] = ttl_seconds

    def delete(self, key):
        self.store.pop(key, None)


class CountingFetcher(ArticleTextPort):
    def __init__(self, text):
        self.text, self.calls = text, 0

    def fetch(self, url):
        self.calls += 1
        return self.text


def _hits():
    return article_fetch_total.labels(result="hit")._value.get()


def test_success_is_cached_with_success_ttl_and_second_call_skips_inner():
    cache, inner = FakeCache(), CountingFetcher("Makale metni")
    f = CachingArticleTextFetcher(inner, cache, ttl_seconds=3600, failure_ttl_seconds=300)
    before = _hits()
    assert f.fetch("https://a.example/1") == "Makale metni"
    assert f.fetch("https://a.example/1") == "Makale metni"
    assert inner.calls == 1
    assert _hits() == before + 1
    assert list(cache.ttls.values()) == [3600]


def test_failure_is_negative_cached_with_short_ttl():
    cache, inner = FakeCache(), CountingFetcher(None)
    f = CachingArticleTextFetcher(inner, cache, ttl_seconds=3600, failure_ttl_seconds=300)
    assert f.fetch("https://a.example/1") is None
    assert f.fetch("https://a.example/1") is None
    assert inner.calls == 1
    assert list(cache.ttls.values()) == [300]


def test_different_urls_use_different_keys():
    cache, inner = FakeCache(), CountingFetcher("x")
    f = CachingArticleTextFetcher(inner, cache, ttl_seconds=10, failure_ttl_seconds=5)
    f.fetch("https://a.example/1")
    f.fetch("https://a.example/2")
    assert inner.calls == 2 and len(cache.store) == 2
    assert all(k.startswith("arttext:") and "a.example" not in k for k in cache.store)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `venv\Scripts\python.exe -m pytest tests/adapters/test_caching_article_text_fetcher.py -v`
Expected: FAIL (`ModuleNotFoundError`).

- [ ] **Step 3: Write minimal implementation**

`src/adapters/scrapers/caching_article_text_fetcher.py`:

```python
"""ArticleTextPort'u CachePort ile saran decorator (CachingQueryExpander ile aynı desen).

Telif kararı: tam metin DB'ye yazılmaz; yalnız bu kısa TTL'li cache'te yaşar. Başarısızlık da
(kısa TTL ile) cache'lenir ki bizi engelleyen bir kaynak her soruda yeniden denenmesin.
`hit` metriği burada basılır; fetched/failed/blocked/too_short sonucunu alttaki somut çekici
kendisi raporlar (tek doğruluk noktası, çift sayım yok).
"""

import hashlib
from typing import Optional

from src.adapters.api.metrics import article_fetch_total
from src.domain.ports.article_text_port import ArticleTextPort
from src.domain.ports.cache_port import CachePort

_FAILURE_SENTINEL = ""


class CachingArticleTextFetcher(ArticleTextPort):
    def __init__(self, inner: ArticleTextPort, cache: CachePort, ttl_seconds: int, failure_ttl_seconds: int):
        self._inner = inner
        self._cache = cache
        self._ttl = ttl_seconds
        self._failure_ttl = failure_ttl_seconds

    def fetch(self, url: str) -> Optional[str]:
        key = "arttext:" + hashlib.sha1(url.encode("utf-8")).hexdigest()
        cached = self._cache.get(key)
        if cached is not None:
            article_fetch_total.labels(result="hit").inc()
            return cached or None
        text = self._inner.fetch(url)
        if text:
            self._cache.set(key, text, ttl_seconds=self._ttl)
        else:
            self._cache.set(key, _FAILURE_SENTINEL, ttl_seconds=self._failure_ttl)
        return text
```

- [ ] **Step 4: Run test to verify it passes**

Run: `venv\Scripts\python.exe -m pytest tests/adapters/test_caching_article_text_fetcher.py -v`
Expected: PASS (3 test).

- [ ] **Step 5: Commit**

```bash
git add src/adapters/scrapers/caching_article_text_fetcher.py tests/adapters/test_caching_article_text_fetcher.py
git commit -m 'feat(rag): makale metni cache decorator i (olumsuz cache dahil)'
```

---

### Task 7: `EvidenceEnricher`

**Files:**
- Create: `src/application/services/evidence_enricher.py`
- Test: `tests/application/test_evidence_enricher.py`

**Interfaces:**
- Consumes: `ArticleTextPort.fetch`, `EmbeddingPort.embed_batch(list[str]) -> list[list[float]]`, `split_paragraphs`, `select_passages` (Task 2).
- Produces: `EvidenceEnricher(fetcher: ArticleTextPort, embedder: EmbeddingPort, *, top_n: int, passage_token_budget: int, total_timeout_seconds: float, enabled: bool = True)`; `.enrich(question: str, articles: Sequence[Article]) -> dict[int, str]` — `article.id` → tek satırlık, `"`-içermeyen pasaj metni. Başarısız/atlanan haber sözlükte YOKTUR.

- [ ] **Step 1: Write the failing test**

`tests/application/test_evidence_enricher.py`:

```python
import threading
import time

from src.application.services.evidence_enricher import EvidenceEnricher
from src.domain.models.article import Article
from src.domain.ports.article_text_port import ArticleTextPort
from src.domain.ports.embedding_port import EmbeddingPort

INJURY = "Kulüp doktoru oyuncunun sakatlığının ciddi olduğunu ve üç hafta sahalardan uzak kalacağını söyledi."
FILLER = "Stadyumun çevresindeki otopark düzenlemeleri ve bilet satış noktaları hakkında genel bilgilendirme yapıldı."


def _article(i, url="auto"):
    a = Article(title=f"T{i}", source="S", url=f"https://s.example/{i}" if url == "auto" else url, content="teaser")
    a.id = i
    return a


class FakeFetcher(ArticleTextPort):
    def __init__(self, texts):
        self.texts, self.calls = texts, []

    def fetch(self, url):
        self.calls.append(url)
        return self.texts.get(url)


class KeywordEmbedder(EmbeddingPort):
    """'sakat' geçen metin [1,0], geçmeyen [0,1] — deterministik."""
    def embed_text(self, text):
        return [1.0, 0.0] if "sakat" in text.lower() else [0.0, 1.0]

    def embed_batch(self, texts):
        return [self.embed_text(t) for t in texts]


class BrokenEmbedder(KeywordEmbedder):
    def embed_batch(self, texts):
        raise RuntimeError("embedder down")


def _enricher(fetcher, embedder=None, **kw):
    kw.setdefault("top_n", 2)
    kw.setdefault("passage_token_budget", 450)
    kw.setdefault("total_timeout_seconds", 5.0)
    return EvidenceEnricher(fetcher, embedder or KeywordEmbedder(), **kw)


def test_selects_question_relevant_passage_from_full_text():
    text = f"{FILLER}\n\n{INJURY}\n\n{FILLER} Ek bilgi."
    out = _enricher(FakeFetcher({"https://s.example/1": text}), passage_token_budget=40).enrich(
        "Oyuncu sakatlıktan ne zaman döner?", [_article(1)]
    )
    assert "üç hafta" in out[1]
    assert "otopark" not in out[1]


def test_only_top_n_articles_are_fetched():
    fetcher = FakeFetcher({f"https://s.example/{i}": INJURY for i in (1, 2, 3)})
    out = _enricher(fetcher, top_n=2).enrich("sakatlık?", [_article(1), _article(2), _article(3)])
    assert sorted(out) == [1, 2]
    assert sorted(fetcher.calls) == ["https://s.example/1", "https://s.example/2"]


def test_failed_fetch_and_missing_url_are_omitted_not_errors():
    fetcher = FakeFetcher({"https://s.example/2": INJURY})
    out = _enricher(fetcher).enrich("sakatlık?", [_article(1), _article(2), _article(3, url="")])
    assert list(out) == [2]


def test_embedder_failure_falls_back_to_no_enrichment():
    fetcher = FakeFetcher({"https://s.example/1": INJURY})
    assert _enricher(fetcher, BrokenEmbedder()).enrich("sakatlık?", [_article(1)]) == {}


def test_disabled_enricher_does_nothing():
    fetcher = FakeFetcher({"https://s.example/1": INJURY})
    assert _enricher(fetcher, enabled=False).enrich("sakatlık?", [_article(1)]) == {}
    assert fetcher.calls == []


def test_quotes_and_newlines_are_flattened_for_the_prompt():
    nasty = 'Doktor "üç hafta" dedi.\nSakatlık durumu hakkında daha fazla bilgi "yakında" verilecek diye eklendi.'
    out = _enricher(FakeFetcher({"https://s.example/1": nasty})).enrich("sakatlık?", [_article(1)])
    assert '"' not in out[1] and "\n" not in out[1]
    assert "üç hafta" in out[1]


def test_articles_are_fetched_in_parallel():
    barrier = threading.Barrier(2, timeout=2.0)

    class BarrierFetcher(ArticleTextPort):
        def fetch(self, url):
            barrier.wait()  # iki çağrı AYNI ANDA içerideyse geçer; seri çalışırsa BrokenBarrierError
            return INJURY

    out = _enricher(BarrierFetcher()).enrich("sakatlık?", [_article(1), _article(2)])
    assert sorted(out) == [1, 2]


def test_total_timeout_returns_what_is_ready_without_waiting_for_slow_fetch():
    release = threading.Event()

    class SlowFetcher(ArticleTextPort):
        def fetch(self, url):
            if url.endswith("/1"):
                return INJURY
            release.wait(timeout=5.0)
            return INJURY

    started = time.monotonic()
    out = _enricher(SlowFetcher(), total_timeout_seconds=0.3).enrich("sakatlık?", [_article(1), _article(2)])
    elapsed = time.monotonic() - started
    release.set()
    assert list(out) == [1]
    assert elapsed < 2.0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `venv\Scripts\python.exe -m pytest tests/application/test_evidence_enricher.py -v`
Expected: FAIL (`ModuleNotFoundError`).

- [ ] **Step 3: Write minimal implementation**

`src/application/services/evidence_enricher.py`:

```python
"""EvidenceEnricher — RAG kanıt paketindeki en iyi haberleri tam metinle zenginleştirir.

Retrieval/özel isim doğrulaması DEĞİŞMEZ: bu sınıf kanıt paketi oluştuktan SONRA çalışır ve
yalnızca her haberin LLM'e giden `content` alanını teaser yerine soruyla en alakalı pasajlarla
değiştirmek için bir sözlük döner. Her adım fail-open'dır: başarısız haber sözlükte yoktur,
çağıran eski `content[:500]` ile devam eder (spec 2026-10-07-rag-tam-metin-design.md).
"""

import logging
from concurrent.futures import ThreadPoolExecutor, wait
from typing import Optional, Sequence

from src.domain.models.article import Article
from src.domain.ports.article_text_port import ArticleTextPort
from src.domain.ports.embedding_port import EmbeddingPort
from src.domain.services.passage_selection import select_passages, split_paragraphs

logger = logging.getLogger(__name__)


class EvidenceEnricher:
    def __init__(
        self,
        fetcher: ArticleTextPort,
        embedder: EmbeddingPort,
        *,
        top_n: int,
        passage_token_budget: int,
        total_timeout_seconds: float,
        enabled: bool = True,
    ):
        self._fetcher = fetcher
        self._embedder = embedder
        self._top_n = top_n
        self._budget = passage_token_budget
        self._total_timeout = total_timeout_seconds
        self._enabled = enabled

    def enrich(self, question: str, articles: Sequence[Article]) -> dict[int, str]:
        if not self._enabled:
            return {}
        targets = [a for a in articles[: self._top_n] if getattr(a, "url", None) and getattr(a, "id", None) is not None]
        if not targets:
            return {}
        pool = ThreadPoolExecutor(max_workers=len(targets))
        futures = {pool.submit(self._passages_for, question, a): a for a in targets}
        done, _ = wait(futures, timeout=self._total_timeout)
        # Bitmeyen thread'ler öldürülemez ama çekicinin kendi zaman aşımı onları sınırlar;
        # istek beklemeden döner.
        pool.shutdown(wait=False, cancel_futures=True)
        enriched: dict[int, str] = {}
        for future in done:
            try:
                passages = future.result()
            except Exception as e:
                logger.warning("Kanıt zenginleştirme başarısız (id=%s): %s", futures[future].id, e)
                continue
            if passages:
                enriched[futures[future].id] = passages
        return enriched

    def _passages_for(self, question: str, article: Article) -> Optional[str]:
        text = self._fetcher.fetch(article.url)
        if not text:
            return None
        paragraphs = split_paragraphs(text)
        if not paragraphs:
            return None
        vectors = self._embedder.embed_batch([question] + paragraphs)
        chosen = select_passages(paragraphs, vectors[0], vectors[1:], self._budget)
        return self._flatten(" ".join(chosen))

    @staticmethod
    def _flatten(text: str) -> str:
        """RAG prompt'u kanıtı `Content: "..."` biçiminde tırnaklı gömer; makale metni
        saldırgan kontrollü olabilir (HN keyfi sitelere link verir) → tırnak ve satır sonu
        bu biçimi bozup talimat enjekte edemesin."""
        return " ".join(text.replace('"', "'").split())
```

- [ ] **Step 4: Run test to verify it passes**

Run: `venv\Scripts\python.exe -m pytest tests/application/test_evidence_enricher.py -v`
Expected: PASS (8 test).

- [ ] **Step 5: Commit**

```bash
git add src/application/services/evidence_enricher.py tests/application/test_evidence_enricher.py
git commit -m 'feat(rag): EvidenceEnricher (paralel cekme + pasaj secimi, fail-open)'
```

---

### Task 8: `NewsService` entegrasyonu, kompozisyon ve sakatlık regresyonu

**Files:**
- Modify: `src/application/services/news_service.py` (constructor satır 113-133; `answer_question` satır 1037-1054; yeni `_enrich_evidence` metodu `_retrieval_candidates`'in yanına)
- Create: `src/adapters/scrapers/article_text_factory.py`
- Modify: `src/dependencies.py` (`get_news_service`, yeni `get_evidence_enricher`)
- Test: `tests/application/test_news_service.py` (dosya sonuna ekle), `tests/adapters/test_article_text_factory.py`

**Interfaces:**
- Consumes: `EvidenceEnricher.enrich(question, articles) -> dict[int, str]` (Task 7), `HttpArticleTextFetcher`, `CachingArticleTextFetcher`, `build_embedder()`, `get_cache()`, `get_search_repository()`.
- Produces: `NewsService(..., evidence_enricher: Optional[EvidenceEnricher] = None)`; `NewsService._enrich_evidence(question, evidence_bundle) -> dict[int, str]` (asla fırlatmaz); `build_evidence_enricher(cache: CachePort, embedder: EmbeddingPort) -> Optional[EvidenceEnricher]` (`settings.rag_fetch_enabled=False` → `None`); `dependencies.get_evidence_enricher() -> Optional[EvidenceEnricher]`.

- [ ] **Step 1: Write the failing tests**

`tests/application/test_news_service.py` sonuna ekle (`make_service_with_qa`, `_evidence_article` aynı dosyada zaten var; import'lar `MagicMock`, `patch` mevcut):

```python
# ── RAG tam metin zenginleştirme (7 Eki 2026) ────────────────────────────────

def test_answer_question_uses_enriched_passages_instead_of_teaser():
    service, mock_repo, mock_qa = make_service_with_qa()
    service.evidence_enricher = MagicMock()
    service.evidence_enricher.enrich.return_value = {1: "Doktor üç hafta dedi."}
    a1, a2 = _evidence_article(1), _evidence_article(2)
    a1.content, a2.content = "teaser bir", "teaser iki"
    mock_repo.get_articles_by_ids.return_value = [a1, a2]
    mock_qa.answer.return_value = {"coverage": "full", "answer": "Cevap.", "used_sources": [1]}
    candidates = [{"id": "1", "score": 0.9, "source": "BBC"}, {"id": "2", "score": 0.8, "source": "CNN"}]
    with patch.object(service, "hybrid_search", return_value=candidates):
        service.answer_question("Ne zaman döner?")
    sources = mock_qa.answer.call_args.kwargs["sources"]
    assert sources[0]["content"] == "Doktor üç hafta dedi."
    assert sources[1]["content"] == "teaser iki"  # zenginleşmeyen haber teaser'ını korur


def test_answer_question_survives_enricher_exception():
    service, mock_repo, mock_qa = make_service_with_qa()
    service.evidence_enricher = MagicMock()
    service.evidence_enricher.enrich.side_effect = RuntimeError("boom")
    article = _evidence_article(1)
    article.content = "teaser"
    mock_repo.get_articles_by_ids.return_value = [article]
    mock_qa.answer.return_value = {"coverage": "full", "answer": "Cevap.", "used_sources": [1]}
    with patch.object(service, "hybrid_search", return_value=[{"id": "1", "score": 0.9, "source": "BBC"}]):
        result = service.answer_question("Ne oldu?")
    assert result["answer"] == "Cevap."
    assert mock_qa.answer.call_args.kwargs["sources"][0]["content"] == "teaser"


def test_injury_return_date_in_article_body_reaches_the_llm_evidence():
    """7 Eki 2026 canlı bulgusu: teaser'da olmayan, makale gövdesinde geçen 'ne zaman döner'
    bilgisi LLM'e hiç ulaşmıyordu ve cevap 'bilmiyorum' idi."""
    from src.application.services.evidence_enricher import EvidenceEnricher
    from src.domain.ports.article_text_port import ArticleTextPort
    from src.domain.ports.embedding_port import EmbeddingPort

    body = (
        "Kulüp doktoru oyuncunun sakatlığının ciddi olduğunu ve üç hafta sahalardan uzak kalacağını açıkladı.\n\n"
        "Stadyum çevresindeki otopark düzenlemeleri hakkında kulüp genel bilgilendirme yaptı bugün."
    )

    class Fetcher(ArticleTextPort):
        def fetch(self, url):
            return body

    class Embedder(EmbeddingPort):
        def embed_text(self, text):
            return [1.0, 0.0] if "sakat" in text.lower() else [0.0, 1.0]

        def embed_batch(self, texts):
            return [self.embed_text(t) for t in texts]

    service, mock_repo, mock_qa = make_service_with_qa()
    service.evidence_enricher = EvidenceEnricher(
        Fetcher(), Embedder(), top_n=2, passage_token_budget=40, total_timeout_seconds=5.0
    )
    article = _evidence_article(1)
    article.content = "Son dakika: yıldız oyuncu sakatlandı."
    mock_repo.get_articles_by_ids.return_value = [article]
    mock_qa.answer.return_value = {"coverage": "full", "answer": "Üç hafta.", "used_sources": [1]}
    with patch.object(service, "hybrid_search", return_value=[{"id": "1", "score": 0.9, "source": "BBC"}]):
        service.answer_question("Oyuncu sakatlıktan ne zaman sahaya döner?")
    content = mock_qa.answer.call_args.kwargs["sources"][0]["content"]
    assert "üç hafta" in content
    assert "otopark" not in content
```

`tests/adapters/test_article_text_factory.py`:

```python
from unittest.mock import MagicMock, patch

from src.adapters.scrapers.article_text_factory import build_evidence_enricher
from src.adapters.scrapers.caching_article_text_fetcher import CachingArticleTextFetcher
from src.application.services.evidence_enricher import EvidenceEnricher


def test_disabled_setting_returns_none():
    with patch("src.adapters.scrapers.article_text_factory.settings") as s:
        s.rag_fetch_enabled = False
        assert build_evidence_enricher(MagicMock(), MagicMock()) is None


def test_enabled_builds_enricher_with_caching_fetcher_from_settings():
    cache, embedder = MagicMock(), MagicMock()
    enricher = build_evidence_enricher(cache, embedder)
    assert isinstance(enricher, EvidenceEnricher)
    assert isinstance(enricher._fetcher, CachingArticleTextFetcher)
    assert enricher._embedder is embedder
    assert enricher._top_n == 2 and enricher._budget == 450 and enricher._total_timeout == 6.0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `venv\Scripts\python.exe -m pytest tests/application/test_news_service.py -k "enrich or injury" tests/adapters/test_article_text_factory.py -v`
Expected: FAIL (`evidence_enricher` alanı/`article_text_factory` yok).

- [ ] **Step 3: Write minimal implementation**

`news_service.py` — `TYPE_CHECKING` bloğuna `from src.application.services.evidence_enricher import EvidenceEnricher` ekle; constructor:

```python
        qa_port: Optional["QuestionAnsweringPort"] = None,
        evidence_enricher: Optional["EvidenceEnricher"] = None,
    ):
        ...
        self.qa_port = qa_port
        self.evidence_enricher = evidence_enricher
```

`_retrieval_candidates`'ten hemen önce yeni metod:

```python
    def _enrich_evidence(self, question: str, evidence_bundle: list) -> dict:
        """En iyi haberlerin tam metin pasajlarını (id -> metin) döner. Fail-open: enricher
        yok/bozuksa boş sözlük, çağıran teaser (`content[:500]`) ile devam eder."""
        if self.evidence_enricher is None:
            return {}
        try:
            return self.evidence_enricher.enrich(question, evidence_bundle)
        except Exception as e:
            logger.warning("RAG kanıt zenginleştirme atlandı: %s", e)
            return {}
```

`answer_question` içinde `evidence_dicts = [` satırından hemen önce `enriched = self._enrich_evidence(question, evidence_bundle)` ekle ve `"content"` satırını (ve üstündeki yorum bloğunu koruyarak) şöyle değiştir:

```python
                # Tam metin pasajı varsa o, yoksa RSS teaser'ı (content[:500] konvansiyonu).
                "content": enriched.get(a.id) or (a.content or "")[:500],
```

`src/adapters/scrapers/article_text_factory.py`:

```python
"""Kanıt zenginleştirici kompozisyon noktası (`cache/factory.py` desenini izler)."""

from typing import Optional

from src.adapters.scrapers.article_text_fetcher import HttpArticleTextFetcher
from src.adapters.scrapers.caching_article_text_fetcher import CachingArticleTextFetcher
from src.application.services.evidence_enricher import EvidenceEnricher
from src.domain.ports.cache_port import CachePort
from src.domain.ports.embedding_port import EmbeddingPort
from src.infrastructure.config.settings import settings


def build_evidence_enricher(cache: CachePort, embedder: EmbeddingPort) -> Optional[EvidenceEnricher]:
    if not settings.rag_fetch_enabled:
        return None
    fetcher = CachingArticleTextFetcher(
        HttpArticleTextFetcher(
            timeout_seconds=settings.rag_fetch_timeout_seconds,
            max_bytes=settings.rag_fetch_max_bytes,
        ),
        cache,
        ttl_seconds=settings.rag_fetch_cache_ttl_seconds,
        failure_ttl_seconds=settings.rag_fetch_failure_ttl_seconds,
    )
    return EvidenceEnricher(
        fetcher,
        embedder,
        top_n=settings.rag_fetch_top_n,
        passage_token_budget=settings.rag_passage_token_budget,
        total_timeout_seconds=settings.rag_fetch_total_timeout_seconds,
    )
```

`src/dependencies.py` — import'lara `from src.adapters.scrapers.article_text_factory import build_evidence_enricher` ve `from src.adapters.search.embedder_factory import build_embedder` ekle; modül değişkeni `_evidence_enricher = None` + `_evidence_enricher_built = False`; `get_cache` altına:

```python
def get_evidence_enricher():
    """RAG tam metin zenginleştirici (singleton). Embedder, arama deposununkini yeniden
    kullanır (yerel 'local' modda modeli ikinci kez RAM'e yüklememek için)."""
    global _evidence_enricher, _evidence_enricher_built
    if not _evidence_enricher_built:
        embedder = getattr(get_search_repository(), "embedder", None) or build_embedder()
        _evidence_enricher = build_evidence_enricher(get_cache(), embedder)
        _evidence_enricher_built = True
    return _evidence_enricher
```

ve `get_news_service`'te `NewsService(..., qa_port=qa_port, evidence_enricher=get_evidence_enricher())`.

- [ ] **Step 4: Run tests to verify they pass**

Run: `venv\Scripts\python.exe -m pytest tests/application/test_news_service.py tests/adapters/test_article_text_factory.py tests/adapters/test_ask_router.py -v`
Expected: PASS (mevcut RAG testleri dahil — `evidence_enricher` varsayılan `None`, davranış değişmez).

- [ ] **Step 5: Commit**

```bash
git add src/application/services/news_service.py src/adapters/scrapers/article_text_factory.py src/dependencies.py tests/application/test_news_service.py tests/adapters/test_article_text_factory.py
git commit -m 'feat(rag): kanit paketine tam metin pasajlari (fail-open) + kompozisyon'
```

---

### Task 9: Tam test paketi, dokümantasyon ve kapanış

**Files:**
- Modify: `docs/CHANGELOG.md` (en üste "7 Ekim — RAG tam metin" girişi)
- Modify: `CLAUDE.md` (BİLİNEN NOTLAR'a tek madde; MEVCUT DURUM "Son oturum" satırı oturum sonunda güncellenir)
- Modify: `docs/superpowers/specs/2026-10-07-rag-tam-metin-design.md` ("Token ve kota" bölümündeki "Hangi kaynağın bloklandığı Grafana'dan görülür" cümlesini düzelt)

- [ ] **Step 1: Tüm backend testlerini çalıştır**

Run: `venv\Scripts\python.exe -m pytest tests/ -q`
Expected: tümü yeşil (≥1090 + yeni testler). Özellikle `tests/infrastructure/test_embedder_image_closure.py`, `test_logger_no_web_deps.py`, `test_image_pipeline.py` yeşil kalmalı; kırılırsa yeni bir modül embedder/scheduler import kapanışına sızmıştır — import'u düzelt, testi gevşetme.

- [ ] **Step 2: Spec'i düzelt**

Spec'te "Hangi kaynağın bloklandığı Grafana'dan görülür." cümlesini şununla değiştir: "Sonuç dağılımı Grafana'dan, hangi host'un bloklandığı/başarısız olduğu `Makale metni engellendi/çekilemedi (<host>)` log satırlarından (Loki) görülür; host Prometheus etiketi DEĞİL (Hacker News keyfi sitelere link verir, kardinalite sınırsız)." ve "Kaynak bazlı `blocked`/`failed` oranı" ifadesini "Loki'de host bazlı `blocked`/`failed` log sayısı" yap. Ayrıca `blocked` tanımına "kaynağın 401/403/429 ile reddetmesi" ekle.

- [ ] **Step 3: CHANGELOG + CLAUDE.md**

`docs/CHANGELOG.md` en üste (mevcut biçimi izle): ne yapıldı (soru anında tam metin, pasaj seçimi, SSRF, cache, metrikler), neden (7 Eki sakatlık bulgusu), tasarım dosyası bağlantısı.

`CLAUDE.md` BİLİNEN NOTLAR'a (yalnız "böyle yap" kuralı):

```
- **RAG kanıtı soru anında makale gövdesiyle zenginleşir (7 Eki 2026):** `EvidenceEnricher` kanıt paketinin ilk `rag_fetch_top_n` haberinin metnini çeker, `select_passages` ile haber başına ~450 token pasaj seçer; tam metin DB'ye YAZILMAZ (yalnız Redis'te 1 saat, başarısızlık 5 dk). Her adım fail-open — çıkmayan kaynak teaser'a düşer. Yeni bir "dış siteye giden HTTP" eklersen `assert_public_http_url` + `BROWSER_USER_AGENT` kullan (SSRF; HN keyfi sitelere link verir). Metrik: `nexstream_article_fetch_total{result}`; host etiketi KOYMA. Kapatma: `RAG_FETCH_ENABLED=false`. Tasarım: `docs/superpowers/specs/2026-10-07-rag-tam-metin-design.md`.
```

- [ ] **Step 4: Commit ve PR hazırlığı**

```bash
git add docs/CHANGELOG.md CLAUDE.md docs/superpowers/specs/2026-10-07-rag-tam-metin-design.md
git commit -m 'docs: RAG tam metin CHANGELOG, CLAUDE.md notu ve spec duzeltmesi'
git push -u origin feat/rag-full-text-evidence
gh pr create --title 'feat(rag): soru aninda makale tam metni (pasaj secimi, SSRF korumali)' --body-file docs/superpowers/specs/2026-10-07-rag-tam-metin-design.md
```

PR açıldıktan sonra dal testinin YEŞİL olduğunu izle (`gh pr checks`). **Merge'i kullanıcı yapar** (`! gh pr merge <N> --squash`; `--auto` KULLANMA — prod deploy tetikler, t3.small'da art arda deploy riskli). Deploy sonrası doğrulama (ben izlerim, kullanıcı merge edince):

1. `RestartCount`/OOM: `for c in $(docker ps -q); do docker inspect --format '{{.Name}} restarts={{.RestartCount}} oom={{.State.OOMKilled}}' $c; done | grep -E 'restarts=[1-9]|oom=true'` (SSM ile) — boş olmalı.
2. Gerçek bir soru sor (Pro hesapla, örn. güncel bir sakatlık haberi) ve cevabın artık gövdedeki detayı içerdiğini kontrol et.
3. Prometheus: `sum by (result) (increase(nexstream_article_fetch_total[1h]))` — `fetched`/`hit` baskın olmalı; `blocked`/`too_short` oranı yüksekse Loki'de host bazlı bak (`docker logs nexstream_engine | grep "Makale metni"`).
4. `nexstream_groq_tokens_total{model="openai/gpt-oss-120b"}` saatlik artışı: soru başına ~+1-1,5K beklenir; RAG payı (~50K/gün) sıkışıyorsa `rag_passage_token_budget`'i düşür.

---

## Self-Review (plan yazarı)

**Spec kapsamı:** Port + saf pasaj seçimi (Task 2) ✔; çıkarıcı (3) ✔; SSRF (4) ✔; çekici: UA, yönlendirme, boyut, içerik türü, süre (5) ✔; cache + negatif cache (6) ✔; enricher: paralel, top-N, toplam süre, fail-open, `enabled` (7) ✔; `answer_question` entegrasyonu + sakatlık regresyonu + DI (8) ✔; ayarlar + metrikler (1) ✔; CHANGELOG/CLAUDE.md/deploy doğrulaması (9) ✔. Spec'le bilinçli sapma: host/kaynak Prometheus etiketi kardinalite nedeniyle yok, Loki log'u var (Task 9 Step 2 spec'i düzeltir); `blocked` = SSRF reddi veya 401/403/429.

**Placeholder taraması:** TBD/"uygun hata yönetimi" yok; her kod adımı tam kod içeriyor.

**Tip tutarlılığı:** `ArticleTextPort.fetch -> Optional[str]` (2) = fetcher (5) = caching (6) = enricher tüketimi (7). `EvidenceEnricher.enrich -> dict[int, str]` (7) = `_enrich_evidence` (8). `select_passages` imzası (2) = enricher çağrısı (7). `settings.rag_fetch_*` adları (1) = factory (8). `article_fetch_total` etiketleri (1) = fetcher/caching (5, 6).

**Bilinen risk / dikkat:** `news_service.py` zaten çok büyük — bu plan oraya yalnız ~12 satır ekler (bölme ayrı iş). `test_slow_body_is_cut_at_deadline` ve `test_extracts_article_paragraphs...` sayısal eşiklere (saat adımı, 200 karakter `<article>` eşiği) dayanır; kırılırsa ilgili adımlardaki notlara bak.
