# RAG Tabanlı Soru-Cevap Implementasyon Planı

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** NexStream'in kendi haber korpusundan kanıt toplayan, kanıt yeterliliğini backend'de deterministik olarak belirleyen ve soru başına en fazla 1 Groq çağrısıyla sentez üreten bir RAG soru-cevap özelliği eklemek (roadmap #13).

**Architecture:** Hexagonal — yeni bir `QuestionAnsweringPort` (Groq adapter'ı, `AnalysisPort`'tan ayrı) + `NewsService.answer_question` orkestrasyonu (mevcut `hybrid_search`/`get_story_cluster`/`get_articles_by_ids`'i olduğu gibi kullanır, yeni bir repository metodu gerekmez) + `POST /api/v1/news/ask` (Pro+ gated, günlük kota sayacına dahil) + frontend'de genel/habere-özel olarak ayrılmış iki sohbet oturumu.

**Tech Stack:** Python/FastAPI/SQLAlchemy (backend), Next.js 14/React/TypeScript (frontend), Groq `openai/gpt-oss-20b` (LLM), mevcut ChromaDB + PostgreSQL hybrid retrieval.

**Spec:** `docs/superpowers/specs/2026-08-26-rag-soru-cevap-design.md`

## Global Constraints

- **En fazla 1 Groq çağrısı/soru, kanıt yoksa 0** — kanıt kapısı (Adım 2) tamamen kod içinde, LLM'e hiç sorulmadan hesaplanır.
- **Ayrı bir "niyet sınıflandırması" LLM çağrısı YOK.**
- **Web'den dış haber araması YOK** — sadece mevcut 17 kaynak korpusu.
- **Ayrı bir `EvidenceRetrievalPort` soyutlaması YOK** — `hybrid_search` + `get_story_cluster` doğrudan kullanılır.
- **Kalıcı sohbet geçmişi (DB tablosu) YOK** — sadece tarayıcı React state'i.
- **LLM kendi kaynağını/URL'sini ÜRETMEZ** — sadece `[1]`, `[2]` gibi numarayla referans verir, gerçek `url`/`source` backend'in retrieval sonucundan gelir.
- **Anonim erişim YOK** — giriş zorunlu + Pro+ tier gating.
- **İkinci bir keyword/uyarı mekanizması YOK** — "haberdar et" aksiyonu mevcut `POST /subscriptions/` (`frequency="instant"`) akışına yönlendirir.
- **`QuestionAnsweringPort.answer()` başarısızlıkta SESSİZ NÖTR FALLBACK vermez** — `AnalysisPort`'un aksine `QuestionAnsweringError` fırlatır (fail-loud).
- **Endpoint `/api/v1/news/ask`'te yaşar** (spec'in "news_router.py" ifadesinden SAPMA — bkz. aşağıdaki not), böylece `usage_tracking_middleware`'in günlük kota sayacına dahil olur; legacy (versiyonsuz) router'a EKLENMEZ.
- **Frontend'de yeni bir test runner'ı (Vitest vb.) KURULMAZ** — session ayrımı mantığı kod incelemesi + manuel QA ile doğrulanır, mevcut `tsc --noEmit` + `npm run build` disiplini korunur.

**Spec'ten kullanıcı onayıyla sapmalar (26 Ağu 2026 brainstorming oturumunda netleşti):**
1. Spec `POST /news/ask`'ı `news_router.py`'de (`get_related` ile "aynı dosya/stil") tanımlıyordu. Kod incelemesinde `get_related`/`get_story_cluster`'ın GERÇEKTE kullanılan kopyalarının `/api/v1/news/...` (`news_router_v1.py`) altında olduğu, frontend'in sadece bu v1 uçlarını çağırdığı ve `usage_tracking_middleware`'in SADECE `/api/v1/` path'lerini kota sayacına işlediği görüldü. Kullanıcı onayıyla: **endpoint SADECE `news_router_v1.py`'ye eklenir**, legacy router'a dokunulmaz.
2. Spec, session ayrımı için bir "birim test" istiyordu ama frontend'de hiç test runner'ı yok (`package.json`'da sadece `dev`/`build`/`start`, hiç `.test.ts` dosyası yok). Kullanıcı onayıyla: **yeni bir test altyapısı kurulmaz**, session ayrımı manuel/canlı QA turuna (Task 13) eklenir.

---

### Task 1: Domain port + hata sınıfı

**Files:**
- Create: `src/domain/ports/question_answering_port.py`

**Interfaces:**
- Produces: `QuestionAnsweringPort` (ABC, tek metot `answer(question: str, sources: list, history: list, corroboration_level: str) -> dict`), `QuestionAnsweringError(Exception)`.

Bu bir ABC + exception tanımı — proje kuralına göre (`query_expansion_port.py`, `analysis_port.py` örnekleri) port dosyalarının kendi başına dedike bir test dosyası yok, somut adapter'lar test edilir (Task 3).

- [ ] **Step 1: Port dosyasını yaz**

```python
"""src/domain/ports/question_answering_port.py

RAG soru-cevap port'u — kanıt paketinden (retrieval sonuçları + tam Article
metadata'sı) yapılandırılmış bir sentez üretir. AnalysisPort'a metot
EKLENMEDİ: proje zaten aynı gerekçeyle QueryExpansionPort'u AnalysisPort'tan
ayrı tutmuş (ikisi de Groq kullanır ama farklı sorumluluklar, ISP ihlali
riski). Somut implementasyon: GroqQuestionAnswerer.
"""

from abc import ABC, abstractmethod


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
        sources: list,
        history: list,
        corroboration_level: str,
    ) -> dict:
        """Dönüş: {"coverage": "full"|"partial"|"none", "answer": str,
        "used_sources": list[int]}. Başarısızlıkta QuestionAnsweringError
        fırlatır (fail-open DEĞİL, fail-loud)."""
        ...
```

- [ ] **Step 2: Import doğrulaması**

Run: `venv\Scripts\python.exe -c "from src.domain.ports.question_answering_port import QuestionAnsweringPort, QuestionAnsweringError; print('ok')"`
Expected: `ok`

- [ ] **Step 3: Commit**

```bash
git add src/domain/ports/question_answering_port.py
git commit -m "feat(rag): QuestionAnsweringPort + QuestionAnsweringError"
```

---

### Task 2: Paylaşılan prompt/parse yardımcıları (`rag_common.py`)

**Files:**
- Create: `src/adapters/analysis/rag_common.py`
- Test: `tests/adapters/test_rag_common.py`

**Interfaces:**
- Consumes: hiçbir şey (saf fonksiyonlar, dış bağımlılık yok).
- Produces: `build_rag_prompt(question: str, sources: list[dict], history: list[dict], corroboration_level: str) -> str`, `parse_rag_json(content: str) -> dict` (dönüş: `{"coverage": str, "answer": str, "used_sources": list[int]}`).
  - `sources` elemanları: `{"index": int, "title": str, "source": str, "sentiment_label": str, "corroboration_count": int, "published_at": str}`.
  - `history` elemanları: `{"role": "user"|"assistant", "content": str}`.

- [ ] **Step 1: Testleri yaz**

```python
# tests/adapters/test_rag_common.py
import json
import pytest
from src.adapters.analysis.rag_common import build_rag_prompt, parse_rag_json


def _source(index=1, title="Test Başlık", source="BBC", sentiment_label="Neutral",
            corroboration_count=1, published_at="2026-08-20"):
    return {"index": index, "title": title, "source": source, "sentiment_label": sentiment_label,
            "corroboration_count": corroboration_count, "published_at": published_at}


def test_build_rag_prompt_includes_numbered_evidence():
    prompt = build_rag_prompt("Ne oldu?", [_source()], [], "single_source")
    assert "[1]" in prompt
    assert "Test Başlık" in prompt
    assert "BBC" in prompt


def test_build_rag_prompt_includes_question():
    prompt = build_rag_prompt("Beşiktaş ne yaptı?", [_source()], [], "single_source")
    assert "Beşiktaş ne yaptı?" in prompt


def test_build_rag_prompt_includes_history():
    history = [{"role": "user", "content": "İstanbul'da ne oldu?"}]
    prompt = build_rag_prompt("Peki ya İzmir'de?", [_source()], history, "single_source")
    assert "İstanbul'da ne oldu?" in prompt


def test_build_rag_prompt_notes_multi_source_corroboration():
    prompt = build_rag_prompt("Ne oldu?", [_source()], [], "multi_source")
    assert "multiple" in prompt.lower()


def test_build_rag_prompt_notes_single_source_caveat():
    prompt = build_rag_prompt("Ne oldu?", [_source()], [], "single_source")
    assert "single source" in prompt.lower()


def test_parse_rag_json_valid_response():
    content = '{"coverage": "full", "answer": "Cevap metni.", "used_sources": [1, 2]}'
    result = parse_rag_json(content)
    assert result == {"coverage": "full", "answer": "Cevap metni.", "used_sources": [1, 2]}


def test_parse_rag_json_strips_markdown_fences():
    content = '```json\n{"coverage": "partial", "answer": "X", "used_sources": [1]}\n```'
    result = parse_rag_json(content)
    assert result["coverage"] == "partial"


def test_parse_rag_json_invalid_coverage_falls_back_to_none():
    content = '{"coverage": "maybe", "answer": "X", "used_sources": []}'
    result = parse_rag_json(content)
    assert result["coverage"] == "none"


def test_parse_rag_json_non_list_used_sources_becomes_empty():
    content = '{"coverage": "full", "answer": "X", "used_sources": "oops"}'
    result = parse_rag_json(content)
    assert result["used_sources"] == []


def test_parse_rag_json_non_int_elements_filtered_out():
    content = '{"coverage": "full", "answer": "X", "used_sources": [1, "2", 3]}'
    result = parse_rag_json(content)
    assert result["used_sources"] == [1, 3]


def test_parse_rag_json_missing_fields_use_safe_defaults():
    content = '{}'
    result = parse_rag_json(content)
    assert result == {"coverage": "none", "answer": "", "used_sources": []}


def test_parse_rag_json_non_string_answer_becomes_empty():
    content = '{"coverage": "full", "answer": 42, "used_sources": []}'
    result = parse_rag_json(content)
    assert result["answer"] == ""


def test_parse_rag_json_raises_on_completely_invalid_json():
    with pytest.raises(json.JSONDecodeError):
        parse_rag_json("Bu JSON değil, düz metin.")
```

- [ ] **Step 2: Testlerin başarısız olduğunu doğrula**

Run: `venv\Scripts\python.exe -m pytest tests/adapters/test_rag_common.py -v`
Expected: FAIL (`ModuleNotFoundError: No module named 'src.adapters.analysis.rag_common'`)

- [ ] **Step 3: `rag_common.py`'ı yaz**

```python
"""src/adapters/analysis/rag_common.py

RAG soru-cevap adapter'larının paylaştığı prompt inşası + JSON ayrıştırma —
common.py'nin (analiz hattı) Q&A karşılığı. Tek implementasyon (Groq) olsa
bile prompt/parse mantığını adapter sınıfından ayrı tutmak, common.py ile
aynı disiplini korur (test edilebilirlik, gelecekte ikinci bir LLM sağlayıcı
eklenirse paylaşılabilirlik).
"""

import json
import re

_VALID_COVERAGE = {"full", "partial", "none"}


def build_rag_prompt(question: str, sources: list, history: list, corroboration_level: str) -> str:
    evidence_lines = "\n".join(
        f'[{s["index"]}] Title: "{s["title"]}" | Source: {s["source"]} | '
        f'Sentiment: {s["sentiment_label"]} | Corroborating sources: {s["corroboration_count"]} | '
        f'Date: {s["published_at"]}'
        for s in sources
    )
    history_text = "\n".join(f'{h["role"]}: {h["content"]}' for h in history) if history else "(none)"
    corroboration_note = (
        "Multiple independent sources are present among the evidence — note where they agree or disagree."
        if corroboration_level == "multi_source"
        else "The evidence rests on a single source — signal this, don't present it as more certain than it is."
    )
    return f"""You are NexStream's evidence-grounded news assistant. Answer the user's question using ONLY the numbered evidence below — never invent a name, number, or detail that isn't in it.

Evidence:
{evidence_lines}

Previous conversation:
{history_text}

Question: {question}

Rules:
- Use ONLY the evidence above. Never invent facts not present in it.
- Reference sources ONLY by their number in brackets, e.g. [1], [2] — never invent a URL or source name.
- Fill "coverage" honestly: "full" if the evidence fully answers the question, "partial" if it only partially answers it (e.g. explains "what" but not "why"), "none" if the evidence doesn't address the question at all.
- Answer in the SAME language as the question (Turkish question -> Turkish answer, English question -> English answer).
- {corroboration_note}

Respond with ONLY this JSON format, no markdown, no explanation:
{{"coverage": "full"|"partial"|"none", "answer": "...", "used_sources": [1, 2]}}"""


def parse_rag_json(content: str) -> dict:
    """Model çıktısını standart RAG sözleşmesine çevirir. Geçersiz/boş JSON'da
    JSONDecodeError fırlatır (adapter'ın retry döngüsü bunu yakalar)."""
    content = re.sub(r"```json|```", "", content).strip()
    match = re.search(r"\{.*\}", content, re.DOTALL)
    result = json.loads(match.group(0)) if match else json.loads(content)

    coverage = result.get("coverage", "none")
    if coverage not in _VALID_COVERAGE:
        coverage = "none"

    used_sources = result.get("used_sources", [])
    if not isinstance(used_sources, list):
        used_sources = []
    used_sources = [i for i in used_sources if isinstance(i, int)]

    answer = result.get("answer", "")
    if not isinstance(answer, str):
        answer = ""

    return {"coverage": coverage, "answer": answer, "used_sources": used_sources}
```

- [ ] **Step 4: Testlerin geçtiğini doğrula**

Run: `venv\Scripts\python.exe -m pytest tests/adapters/test_rag_common.py -v`
Expected: 13 passed

- [ ] **Step 5: Commit**

```bash
git add src/adapters/analysis/rag_common.py tests/adapters/test_rag_common.py
git commit -m "feat(rag): rag_common prompt builder + JSON parser"
```

---

### Task 3: `GroqQuestionAnswerer` adapter + factory

**Files:**
- Create: `src/adapters/analysis/groq_question_answerer.py`
- Modify: `src/adapters/analysis/factory.py`
- Test: `tests/adapters/test_groq_question_answerer.py`

**Interfaces:**
- Consumes: `QuestionAnsweringPort`, `QuestionAnsweringError` (Task 1), `build_rag_prompt`, `parse_rag_json` (Task 2), `groq_latency_seconds`, `groq_rate_limit_total` (mevcut `src/adapters/api/metrics.py`).
- Produces: `GroqQuestionAnswerer(QuestionAnsweringPort)`, `factory.build_question_answerer() -> QuestionAnsweringPort`.

- [ ] **Step 1: Testleri yaz**

```python
# tests/adapters/test_groq_question_answerer.py
import pytest
from unittest.mock import patch, MagicMock
from src.adapters.analysis.groq_question_answerer import GroqQuestionAnswerer
from src.domain.ports.question_answering_port import QuestionAnsweringError


def make_mock_response(content: str, status_code: int = 200):
    mock = MagicMock()
    mock.status_code = status_code
    mock.json.return_value = {"choices": [{"message": {"content": content}}]}
    mock.raise_for_status = MagicMock()
    return mock


def _sources():
    return [{"index": 1, "title": "Başlık", "source": "BBC", "sentiment_label": "Neutral",
             "corroboration_count": 1, "published_at": "2026-08-20"}]


def test_answer_returns_parsed_result():
    qa = GroqQuestionAnswerer()
    response_json = '{"coverage": "full", "answer": "Cevap.", "used_sources": [1]}'
    with patch("requests.post", return_value=make_mock_response(response_json)):
        result = qa.answer("Ne oldu?", _sources(), [], "single_source")
    assert result["coverage"] == "full"
    assert result["answer"] == "Cevap."
    assert result["used_sources"] == [1]


def test_answer_retries_on_rate_limit():
    qa = GroqQuestionAnswerer()
    rate_limit_response = MagicMock()
    rate_limit_response.status_code = 429
    rate_limit_response.headers = {"retry-after": "1"}
    rate_limit_response.raise_for_status = MagicMock()
    success = make_mock_response('{"coverage": "full", "answer": "OK", "used_sources": [1]}')
    with patch("requests.post", side_effect=[rate_limit_response, success]), patch("time.sleep"):
        result = qa.answer("Ne oldu?", _sources(), [], "single_source")
    assert result["coverage"] == "full"


def test_answer_raises_after_exhausting_json_parse_errors():
    qa = GroqQuestionAnswerer()
    bad_response = make_mock_response("Bu JSON değil.")
    with patch("requests.post", return_value=bad_response):
        with pytest.raises(QuestionAnsweringError):
            qa.answer("Ne oldu?", _sources(), [], "single_source")


def test_answer_raises_on_connection_error():
    """AnalysisPort'un aksine bu port'ta sessiz nötr fallback YOK — spec 'Amaç'
    bölümü: 'kibarca uydurulmuş' bir cevap vermek açık hatadan daha kötü."""
    qa = GroqQuestionAnswerer()
    with patch("requests.post", side_effect=Exception("Connection refused")), \
         patch("src.adapters.analysis.groq_question_answerer.time.sleep"):
        with pytest.raises(QuestionAnsweringError):
            qa.answer("Ne oldu?", _sources(), [], "single_source")


def test_answer_passes_corroboration_level_into_prompt():
    qa = GroqQuestionAnswerer()
    response_json = '{"coverage": "full", "answer": "OK", "used_sources": [1]}'
    captured = {}

    def capture(*args, **kwargs):
        captured["prompt"] = kwargs["json"]["messages"][0]["content"]
        return make_mock_response(response_json)

    with patch("requests.post", side_effect=capture):
        qa.answer("Ne oldu?", _sources(), [], "multi_source")
    assert "multiple" in captured["prompt"].lower()


# ── factory ──────────────────────────────────────────────────────────────

def test_build_question_answerer_returns_groq_adapter():
    from src.adapters.analysis.factory import build_question_answerer
    assert isinstance(build_question_answerer(), GroqQuestionAnswerer)
```

- [ ] **Step 2: Testlerin başarısız olduğunu doğrula**

Run: `venv\Scripts\python.exe -m pytest tests/adapters/test_groq_question_answerer.py -v`
Expected: FAIL (`ModuleNotFoundError`)

- [ ] **Step 3: `groq_question_answerer.py`'ı yaz**

```python
"""src/adapters/analysis/groq_question_answerer.py

RAG soru-cevap adapter'ı — kanıt paketinden TEK bir Groq çağrısıyla
yapılandırılmış bir sentez üretir (coverage/answer/used_sources).

GroqAnalyzer'daki rate-limit/retry HTTP deseninin (429 → Retry-After bekle,
5 deneme) birebir aynısı, ayrı bir prompt/parse mantığıyla (rag_common.py).

AnalysisPort'un aksine SESSİZ NÖTR FALLBACK YOK: tüm denemeler başarısız
olursa QuestionAnsweringError fırlatılır — bir soruya "kibarca uydurulmuş"
bir cevap vermek, açık bir hata vermekten daha kötü (bkz. spec "Amaç").
"""

import json
import logging
import time

import requests

from src.domain.ports.question_answering_port import QuestionAnsweringPort, QuestionAnsweringError
from src.adapters.analysis.rag_common import build_rag_prompt, parse_rag_json
from src.infrastructure.config.settings import settings
from src.adapters.api.metrics import groq_latency_seconds, groq_rate_limit_total

logger = logging.getLogger(__name__)


class GroqQuestionAnswerer(QuestionAnsweringPort):
    def __init__(self):
        self.api_key = settings.groq_api_key
        self.model = "openai/gpt-oss-20b"
        self.api_url = "https://api.groq.com/openai/v1/chat/completions"

    def answer(self, question: str, sources: list, history: list, corroboration_level: str) -> dict:
        prompt = build_rag_prompt(question, sources, history, corroboration_level)
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 800,
            "temperature": 0.2,
            "reasoning_effort": "low",
        }

        for attempt in range(5):
            try:
                start = time.time()
                r = requests.post(self.api_url, headers=headers, json=payload, timeout=30)
                groq_latency_seconds.observe(time.time() - start)

                if r.status_code == 429:
                    groq_rate_limit_total.inc()
                    wait = int(r.headers.get("retry-after", 5))
                    logger.warning("Groq rate limit (soru-cevap), %ds bekleniyor...", wait)
                    time.sleep(wait)
                    continue

                r.raise_for_status()
                content = r.json()["choices"][0]["message"]["content"]
                return parse_rag_json(content)

            except json.JSONDecodeError:
                logger.warning("Groq soru-cevap JSON parse hatası, deneme %d", attempt + 1)
                continue
            except Exception as e:
                logger.error("Groq soru-cevap hatası: %s", e)
                if attempt < 2:
                    time.sleep(5)
                continue

        raise QuestionAnsweringError("Groq: tüm denemeler başarısız (soru-cevap)")
```

- [ ] **Step 4: `factory.py`'a `build_question_answerer` ekle**

`src/adapters/analysis/factory.py` içine (dosyanın başındaki import bloğuna ve sonuna):

```python
from src.adapters.analysis.groq_question_answerer import GroqQuestionAnswerer
from src.domain.ports.question_answering_port import QuestionAnsweringPort
```

(mevcut import bloğunun altına ekle), ve dosyanın sonuna:

```python
def build_question_answerer() -> QuestionAnsweringPort:
    """RAG soru-cevap kompozisyon noktası. Tek implementasyon var (Groq) —
    HuggingFace'in Q&A karşılığı yok, build_analyzer()'daki fallback zinciri
    YOK (YAGNI, bkz. spec 'Mimari & Bileşenler')."""
    return GroqQuestionAnswerer()
```

- [ ] **Step 5: Testlerin geçtiğini doğrula**

Run: `venv\Scripts\python.exe -m pytest tests/adapters/test_groq_question_answerer.py -v`
Expected: 7 passed

- [ ] **Step 6: Commit**

```bash
git add src/adapters/analysis/groq_question_answerer.py src/adapters/analysis/factory.py tests/adapters/test_groq_question_answerer.py
git commit -m "feat(rag): GroqQuestionAnswerer adapter + factory wiring"
```

---

### Task 4: Pydantic şemaları

**Files:**
- Modify: `src/domain/schemas/news_schema.py`

**Interfaces:**
- Produces: `AskMessage`, `AskRequest`, `RagSource`, `RagAnswerResponse` (Pydantic modelleri).

`news_schema.py`'deki hiçbir mevcut şemanın dedike bir test dosyası yok (router testleri üzerinden dolaylı doğrulanıyor) — bu görev için de aynı desen, doğrulama Task 7'nin router testlerinde yapılır.

- [ ] **Step 1: Şemaları dosyanın sonuna ekle**

```python
# v2.6 — RAG soru-cevap ("kanıta dayalı haber asistanı", roadmap #13).
class AskMessage(BaseModel):
    role: str = Field(..., pattern="^(user|assistant)$")
    content: str = Field(..., min_length=1, max_length=2000)


class AskRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=500)
    article_id: Optional[int] = None
    # history uzunluğu sınırlanır: kota/prompt-boyutu koruması, paylaşılan
    # Groq kotasını (bkz. CLAUDE.md BİLİNEN NOTLAR) tek bir istekle şişirmeyi
    # önler — SearchRequest.n_results'ın üst sınır deseniyle aynı disiplin.
    history: List[AskMessage] = Field(default_factory=list, max_length=20)


class RagSource(BaseModel):
    index: int
    title: str
    source: str
    url: str


class RagAnswerResponse(BaseModel):
    answer: str
    coverage: str            # "full" | "partial" | "none"
    corroboration_level: str # "single_source" | "multi_source" | "none"
    sources: List[RagSource] = Field(default_factory=list)
    suggest_alert: bool = False
```

- [ ] **Step 2: Import doğrulaması**

Run: `venv\Scripts\python.exe -c "from src.domain.schemas.news_schema import AskMessage, AskRequest, RagSource, RagAnswerResponse; print('ok')"`
Expected: `ok`

- [ ] **Step 3: Commit**

```bash
git add src/domain/schemas/news_schema.py
git commit -m "feat(rag): AskRequest/RagAnswerResponse Pydantic şemaları"
```

---

### Task 5: `NewsService.answer_question` orkestrasyonu

**Files:**
- Modify: `src/application/services/news_service.py`
- Modify: `src/infrastructure/config/settings.py`
- Test: `tests/application/test_news_service.py`

**Interfaces:**
- Consumes: `self.hybrid_search` (mevcut), `self.get_story_cluster` (mevcut), `self.repository.get_article_by_id`/`get_articles_by_ids` (mevcut), `self.qa_port.answer(...)` (Task 3), `settings.rag_retrieval_threshold` (bu görevde eklenir).
- Produces: `NewsService.answer_question(question: str, article_id: Optional[int] = None, history: Optional[list] = None) -> Optional[dict]` — dönüş `None` sadece habere özel modda `article_id` bulunamadığında (router 404'e çevirir); aksi halde `{"answer", "coverage", "corroboration_level", "sources", "suggest_alert"}` şeklinde bir dict. Başarısızlıkta `QuestionAnsweringError` fırlatır (yakalanmaz, yukarı geçer).

- [ ] **Step 1: `settings.py`'a eşik değerini ekle**

`src/infrastructure/config/settings.py` içinde `search_query_expansion_enabled: bool = True` satırının hemen altına:

```python

    # ── RAG soru-cevap (roadmap #13) ────────────────────────────────────────
    # Kanıt kapısı eşiği: hybrid_search/get_story_cluster skoru bu değerin
    # altındaki adaylar Groq'a hiç gönderilmez (NewsService.answer_question).
    # Gerçek sorularla kalibre edilecek — bkz. spec "Açık Noktalar".
    rag_retrieval_threshold: float = 0.5
```

- [ ] **Step 2: Testleri yaz**

`tests/application/test_news_service.py` dosyasının sonuna ekle (dosyanın başında zaten `from unittest.mock import MagicMock, AsyncMock, patch` ve `from src.domain.models.article import Article` import edilmiş durumda):

```python
# ── answer_question (RAG) ────────────────────────────────────────────────────

from src.domain.ports.question_answering_port import QuestionAnsweringError


def make_service_with_qa():
    service, mock_repo, mock_analyzer = make_service()
    mock_qa = MagicMock()
    service.qa_port = mock_qa
    return service, mock_repo, mock_qa


def _evidence_article(article_id, source="BBC", sentiment_label="Neutral", corroboration_count=0):
    a = Article(title=f"Article {article_id}", source=source, url=f"http://x/{article_id}", content="content")
    a.id = article_id
    a.sentiment_label = sentiment_label
    a.corroboration_count = corroboration_count
    return a


def test_answer_question_no_evidence_skips_groq_call():
    """Retrieval boşsa (genel mod) Groq HİÇ ÇAĞRILMAZ + NO_EVIDENCE + suggest_alert=True."""
    service, mock_repo, mock_qa = make_service_with_qa()
    with patch.object(service, "hybrid_search", return_value=[]):
        result = service.answer_question("Beşiktaş'ın sağ kanat transferi ne durumda?")
    mock_qa.answer.assert_not_called()
    assert result["coverage"] == "none"
    assert result["suggest_alert"] is True
    assert result["sources"] == []


def test_answer_question_article_mode_invalid_id_returns_none():
    service, mock_repo, mock_qa = make_service_with_qa()
    mock_repo.get_article_by_id.return_value = None
    result = service.answer_question("Bu haberde ne oldu?", article_id=999)
    assert result is None
    mock_qa.answer.assert_not_called()


def test_answer_question_raises_when_qa_port_none():
    """qa_port opsiyonel bağımlılık — None ise anlamlı bir hata (fail-loud)."""
    service, mock_repo, _ = make_service()
    with pytest.raises(QuestionAnsweringError):
        service.answer_question("Ne oldu?")


def test_answer_question_corroboration_level_multi_source():
    service, mock_repo, mock_qa = make_service_with_qa()
    candidates = [
        {"id": "1", "score": 0.9, "source": "BBC"},
        {"id": "2", "score": 0.8, "source": "Sözcü"},
    ]
    mock_repo.get_articles_by_ids.return_value = [
        _evidence_article(1, source="BBC"), _evidence_article(2, source="Sözcü"),
    ]
    mock_qa.answer.return_value = {"coverage": "full", "answer": "Cevap.", "used_sources": [1, 2]}
    with patch.object(service, "hybrid_search", return_value=candidates):
        result = service.answer_question("Ne oldu?")
    assert result["corroboration_level"] == "multi_source"
    assert mock_qa.answer.call_args.kwargs["corroboration_level"] == "multi_source"


def test_answer_question_corroboration_level_single_source():
    service, mock_repo, mock_qa = make_service_with_qa()
    candidates = [{"id": "1", "score": 0.9, "source": "BBC"}]
    mock_repo.get_articles_by_ids.return_value = [_evidence_article(1, source="BBC")]
    mock_qa.answer.return_value = {"coverage": "full", "answer": "Cevap.", "used_sources": [1]}
    with patch.object(service, "hybrid_search", return_value=candidates):
        result = service.answer_question("Ne oldu?")
    assert result["corroboration_level"] == "single_source"


def test_answer_question_ignores_model_answer_when_coverage_none():
    """Model coverage='none' derse 'answer' alanı NE OLURSA OLSUN göz ardı
    edilir, dürüst şablona düşülür (Adım 6, spec)."""
    service, mock_repo, mock_qa = make_service_with_qa()
    candidates = [{"id": "1", "score": 0.9, "source": "BBC"}]
    mock_repo.get_articles_by_ids.return_value = [_evidence_article(1)]
    mock_qa.answer.return_value = {"coverage": "none", "answer": "UYDURULMUŞ CEVAP", "used_sources": [1]}
    with patch.object(service, "hybrid_search", return_value=candidates):
        result = service.answer_question("İlgisiz bir soru")
    assert result["answer"] != "UYDURULMUŞ CEVAP"
    assert result["coverage"] == "none"
    assert result["sources"] == []


def test_answer_question_clamps_out_of_range_used_sources():
    service, mock_repo, mock_qa = make_service_with_qa()
    candidates = [{"id": "1", "score": 0.9, "source": "BBC"}]
    mock_repo.get_articles_by_ids.return_value = [_evidence_article(1)]
    mock_qa.answer.return_value = {"coverage": "full", "answer": "Cevap.", "used_sources": [1, 99]}
    with patch.object(service, "hybrid_search", return_value=candidates):
        result = service.answer_question("Ne oldu?")
    assert [s["index"] for s in result["sources"]] == [1]


def test_answer_question_article_mode_target_always_included():
    """Habere özel modda hedef, retrieval eşiğinden MUAF — story cluster boş
    dönse bile hedefin kendisi kanıt paketine girer, Groq çağrılır."""
    service, mock_repo, mock_qa = make_service_with_qa()
    target = _evidence_article(5, source="TRT")
    mock_repo.get_article_by_id.return_value = target
    mock_repo.get_articles_by_ids.return_value = [target]
    mock_qa.answer.return_value = {"coverage": "full", "answer": "Cevap.", "used_sources": [1]}
    with patch.object(service, "get_story_cluster", return_value={"article_id": 5, "sources": []}):
        result = service.answer_question("Bu haberde ne oldu?", article_id=5)
    mock_qa.answer.assert_called_once()
    assert result["coverage"] == "full"


def test_answer_question_passes_history_to_qa_port():
    service, mock_repo, mock_qa = make_service_with_qa()
    candidates = [{"id": "1", "score": 0.9, "source": "BBC"}]
    mock_repo.get_articles_by_ids.return_value = [_evidence_article(1)]
    mock_qa.answer.return_value = {"coverage": "full", "answer": "Cevap.", "used_sources": [1]}
    history = [{"role": "user", "content": "İstanbul'da ne oldu?"}, {"role": "assistant", "content": "..."}]
    with patch.object(service, "hybrid_search", return_value=candidates):
        service.answer_question("Peki ya İzmir'de?", history=history)
    assert mock_qa.answer.call_args.kwargs["history"] == history


def test_no_evidence_response_turkish_question_returns_turkish_text():
    service, mock_repo, mock_qa = make_service_with_qa()
    with patch.object(service, "hybrid_search", return_value=[]):
        result = service.answer_question("Beşiktaş'ın yeni hocası kim olacak?")
    assert result["answer"] == NewsService._NO_EVIDENCE_TEXT["TR"]


def test_no_evidence_response_english_question_returns_english_text():
    service, mock_repo, mock_qa = make_service_with_qa()
    with patch.object(service, "hybrid_search", return_value=[]):
        result = service.answer_question("Who will be the new coach?")
    assert result["answer"] == NewsService._NO_EVIDENCE_TEXT["EN"]
```

- [ ] **Step 3: Testlerin başarısız olduğunu doğrula**

Run: `venv\Scripts\python.exe -m pytest tests/application/test_news_service.py -k answer_question -v`
Expected: FAIL (`AttributeError: 'NewsService' object has no attribute 'answer_question'` / `qa_port`)

- [ ] **Step 4: `news_service.py`'a `answer_question` ve yardımcılarını ekle**

`src/application/services/news_service.py` dosyasının başındaki gerçek (TYPE_CHECKING dışı) importlara ekle:

```python
from src.domain.ports.question_answering_port import QuestionAnsweringError
```

`TYPE_CHECKING` bloğuna ekle:

```python
    from src.domain.ports.question_answering_port import QuestionAnsweringPort
```

`__init__` imzasına son parametre olarak ekle (mevcut `web_push` parametresinden sonra):

```python
        web_push: Optional["WebPushPort"] = None,
        qa_port: Optional["QuestionAnsweringPort"] = None,
    ):
        self.repository = repository
        self.analyzer = analyzer
        self.search_repository = search_repository
        self.subscriber_repository = subscriber_repository
        self.email_port = email_port
        self.query_expander = query_expander
        self.push_repository = push_repository
        self.web_push = web_push
        self.qa_port = qa_port
```

`get_story_cluster` metodundan hemen sonra (bir sonraki metot `_send_keyword_alerts`'ten önce) şu bloğu ekle:

```python
    # ── RAG soru-cevap (roadmap #13) ────────────────────────────────────────
    # Kanıt kapısı deterministik kodda çözülür, soru başına en fazla 1 Groq
    # çağrısı (kanıt yoksa 0). Bkz. spec
    # docs/superpowers/specs/2026-08-26-rag-soru-cevap-design.md.

    _NO_EVIDENCE_TEXT = {
        "TR": "Takip ettiğim kaynaklarda bu konuda doğrulanabilir bir gelişme bulunmuyor.",
        "EN": "I don't have verifiable coverage of this topic in the sources I track.",
    }
    _TR_CHARS = set("ğüşıöçĞÜŞİÖÇ")

    @staticmethod
    def _looks_turkish(text: str) -> bool:
        """Kaba ama ücretsiz bir dil sezgisi — SADECE Groq'a hiç gidilmeyen
        (kanıt kapısı kapalı) yolda kullanılan şablon cevabın dilini seçer.
        LLM'in ürettiği gerçek cevaplar zaten prompt'taki bilingual kuralla
        kendi dilini seçiyor; burada sadece kanıtsız durum için ucuz bir
        varsayım gerekiyor. Türkçe'ye özgü karakter yoksa EN varsayılır —
        aksansız Türkçe sorularda (nadir) yanlış tahmin edebilir, kabul
        edilebilir bir sınır (sadece kanıt-yok şablonunu etkiler)."""
        return any(ch in NewsService._TR_CHARS for ch in text)

    def _no_evidence_response(self, question: str, general_mode: bool) -> dict:
        lang = "TR" if self._looks_turkish(question) else "EN"
        return {
            "answer": self._NO_EVIDENCE_TEXT[lang],
            "coverage": "none",
            "corroboration_level": "none",
            "sources": [],
            "suggest_alert": general_mode,
        }

    def _retrieval_candidates(self, question: str, target: Optional[Article]) -> list:
        """Genel modda hybrid_search, habere özel modda get_story_cluster
        sonuçlarını ortak bir şekle (id/score/source, id daima int) normalize
        eder. Malformed-result guard: id/score çözülemeyen adaylar sessizce
        elenir (bkz. CLAUDE.md 'arama ilişkisel genişletme' dersi, aynı
        defect class)."""
        raw = self.hybrid_search(question, n_results=8) if target is None \
            else self.get_story_cluster(target.id, limit=6).get("sources", [])
        candidates = []
        for c in raw:
            try:
                cid = int(c["id"])
            except (KeyError, TypeError, ValueError):
                continue
            candidates.append({"id": cid, "score": float(c.get("score", 0.0)), "source": c.get("source", "")})
        return candidates

    def answer_question(self, question: str, article_id: Optional[int] = None,
                         history: Optional[list] = None) -> Optional[dict]:
        """Kanıt kapısı: retrieval skorları `settings.rag_retrieval_threshold`
        altındaysa Groq'a HİÇ gidilmez (kota harcanmaz). Habere özel modda
        hedef makale eşikten muaftır — kullanıcı zaten O haberi soruyor.
        Dönüş `None` ise (sadece habere özel modda) `article_id` bulunamadı
        demektir, router 404 döner. Groq tüm denemeleri tüketirse
        `QuestionAnsweringError` fırlatır (fail-open DEĞİL, bkz. spec 'Amaç')."""
        if self.qa_port is None:
            raise QuestionAnsweringError("Soru-cevap servisi yapılandırılmamış")
        history = history or []

        target: Optional[Article] = None
        if article_id is not None:
            target = self.repository.get_article_by_id(article_id)
            if target is None:
                return None

        candidates = self._retrieval_candidates(question, target)
        threshold = settings.rag_retrieval_threshold
        passing = [c for c in candidates if c["score"] >= threshold]
        if target is not None:
            # Hedef eşikten muaf — kullanıcı zaten bu haberi soruyor, listenin
            # başına eklenir (kanıt paketinde her zaman [1] o olur).
            passing = [{"id": target.id, "source": target.source}] + \
                [c for c in passing if c["id"] != target.id]

        if not passing:
            return self._no_evidence_response(question, general_mode=target is None)

        distinct_sources = {c["source"] for c in passing if c["source"]}
        corroboration_level = "multi_source" if len(distinct_sources) >= 2 else "single_source"

        articles_by_id = {a.id: a for a in self.repository.get_articles_by_ids([c["id"] for c in passing])}
        if target is not None:
            articles_by_id[target.id] = target  # her ihtimale karşı en taze halini kullan

        evidence_bundle = [articles_by_id[c["id"]] for c in passing if c["id"] in articles_by_id]
        if not evidence_bundle:
            return self._no_evidence_response(question, general_mode=target is None)

        evidence_dicts = [
            {
                "index": i + 1,
                "title": a.title,
                "source": a.source,
                "sentiment_label": a.sentiment_label or "Neutral",
                "corroboration_count": a.corroboration_count or 0,
                "published_at": (a.published_at or a.created_at).strftime("%Y-%m-%d")
                    if (a.published_at or a.created_at) else "",
            }
            for i, a in enumerate(evidence_bundle)
        ]

        result = self.qa_port.answer(
            question=question, sources=evidence_dicts, history=history,
            corroboration_level=corroboration_level,
        )

        if result["coverage"] == "none":
            return self._no_evidence_response(question, general_mode=target is None)

        used = [i for i in result.get("used_sources", []) if isinstance(i, int) and 1 <= i <= len(evidence_bundle)]
        sources = [
            {"index": i, "title": evidence_bundle[i - 1].title,
             "source": evidence_bundle[i - 1].source, "url": evidence_bundle[i - 1].url}
            for i in used
        ]
        return {
            "answer": result["answer"],
            "coverage": result["coverage"],
            "corroboration_level": corroboration_level,
            "sources": sources,
            "suggest_alert": False,
        }
```

- [ ] **Step 5: Testlerin geçtiğini doğrula**

Run: `venv\Scripts\python.exe -m pytest tests/application/test_news_service.py -k answer_question -v`
Expected: 11 passed

- [ ] **Step 6: Tam backend test paketini çalıştır (regresyon)**

Run: `venv\Scripts\python.exe -m pytest tests/ -q`
Expected: hepsi yeşil (önceki toplam + bu göreve kadar eklenen testler)

- [ ] **Step 7: Commit**

```bash
git add src/application/services/news_service.py src/infrastructure/config/settings.py tests/application/test_news_service.py
git commit -m "feat(rag): NewsService.answer_question orkestrasyonu"
```

---

### Task 6: `POST /api/v1/news/ask` endpoint + DI wiring

**Files:**
- Modify: `src/adapters/api/routers/v1/news_router_v1.py`
- Modify: `src/dependencies.py`
- Test: `tests/adapters/test_ask_router.py`

**Interfaces:**
- Consumes: `NewsService.answer_question` (Task 5), `AskRequest`/`RagAnswerResponse` (Task 4), `QuestionAnsweringError` (Task 1), `check_tier_limit`/`user_effective_tier`/`tier_at_least` (mevcut `auth_utils.py`), `build_question_answerer` (Task 3).
- Produces: `POST /api/v1/news/ask` — 200 (`RagAnswerResponse`), 403 (Free/anonim), 404 (geçersiz `article_id`), 503 (`QuestionAnsweringError`), 422 (boş `question`).

- [ ] **Step 1: Testleri yaz**

```python
# tests/adapters/test_ask_router.py
from unittest.mock import MagicMock

from src.domain.models.user import User, UserTier
from src.adapters.api.auth_utils import check_tier_limit
from src.domain.ports.question_answering_port import QuestionAnsweringError


def _override(app_client, mock_service):
    from src.dependencies import get_news_service
    app_client.app.dependency_overrides[get_news_service] = lambda: mock_service


def _override_pro(app_client, mock_service):
    _override(app_client, mock_service)
    pro = User(id=1, email="pro@test.com", password_hash="h", tier=UserTier.PRO)
    app_client.app.dependency_overrides[check_tier_limit] = lambda: pro


def _clear(app_client):
    app_client.app.dependency_overrides.clear()


_PAYLOAD = {
    "answer": "Cevap burada.",
    "coverage": "full",
    "corroboration_level": "multi_source",
    "sources": [{"index": 1, "title": "Başlık", "source": "BBC", "url": "http://x"}],
    "suggest_alert": False,
}


def test_ask_endpoint_returns_payload_for_pro_user(app_client):
    mock_service = MagicMock()
    mock_service.answer_question.return_value = _PAYLOAD
    _override_pro(app_client, mock_service)
    try:
        r = app_client.post("/api/v1/news/ask", json={"question": "Ne oldu?"})
    finally:
        _clear(app_client)

    assert r.status_code == 200
    data = r.json()
    assert data["answer"] == "Cevap burada."
    assert data["coverage"] == "full"
    assert data["sources"][0]["source"] == "BBC"


def test_ask_endpoint_blocked_for_free_tier(app_client):
    mock_service = MagicMock()
    _override(app_client, mock_service)
    free = User(id=1, email="free@test.com", password_hash="h", tier=UserTier.FREE)
    app_client.app.dependency_overrides[check_tier_limit] = lambda: free
    try:
        r = app_client.post("/api/v1/news/ask", json={"question": "Ne oldu?"})
    finally:
        _clear(app_client)
    assert r.status_code == 403
    mock_service.answer_question.assert_not_called()


def test_ask_endpoint_blocked_for_anonymous(app_client):
    mock_service = MagicMock()
    _override(app_client, mock_service)
    app_client.app.dependency_overrides[check_tier_limit] = lambda: None
    try:
        r = app_client.post("/api/v1/news/ask", json={"question": "Ne oldu?"})
    finally:
        _clear(app_client)
    assert r.status_code == 403


def test_ask_endpoint_404_when_article_not_found(app_client):
    mock_service = MagicMock()
    mock_service.answer_question.return_value = None
    _override_pro(app_client, mock_service)
    try:
        r = app_client.post("/api/v1/news/ask", json={"question": "Ne oldu?", "article_id": 999})
    finally:
        _clear(app_client)
    assert r.status_code == 404


def test_ask_endpoint_503_on_question_answering_error(app_client):
    mock_service = MagicMock()
    mock_service.answer_question.side_effect = QuestionAnsweringError("Groq: tüm denemeler başarısız")
    _override_pro(app_client, mock_service)
    try:
        r = app_client.post("/api/v1/news/ask", json={"question": "Ne oldu?"})
    finally:
        _clear(app_client)
    assert r.status_code == 503


def test_ask_endpoint_passes_article_id_and_history(app_client):
    mock_service = MagicMock()
    mock_service.answer_question.return_value = _PAYLOAD
    _override_pro(app_client, mock_service)
    try:
        app_client.post("/api/v1/news/ask", json={
            "question": "Peki ya İzmir'de?",
            "article_id": 42,
            "history": [{"role": "user", "content": "İstanbul'da ne oldu?"},
                        {"role": "assistant", "content": "..."}],
        })
    finally:
        _clear(app_client)

    mock_service.answer_question.assert_called_once_with(
        "Peki ya İzmir'de?",
        article_id=42,
        history=[{"role": "user", "content": "İstanbul'da ne oldu?"},
                 {"role": "assistant", "content": "..."}],
    )


def test_ask_endpoint_rejects_empty_question(app_client):
    r = app_client.post("/api/v1/news/ask", json={"question": ""})
    assert r.status_code == 422


def test_ask_endpoint_not_registered_on_legacy_router(app_client):
    """Bilinçli tasarım kararı (26 Ağu 2026): endpoint SADECE /api/v1'de,
    kota sayacına (usage_tracking_middleware) dahil olsun diye."""
    r = app_client.post("/news/ask", json={"question": "Ne oldu?"})
    assert r.status_code == 404
```

- [ ] **Step 2: Testlerin başarısız olduğunu doğrula**

Run: `venv\Scripts\python.exe -m pytest tests/adapters/test_ask_router.py -v`
Expected: FAIL (404 — route henüz yok; son test hariç hepsi)

- [ ] **Step 3: `dependencies.py`'a `qa_port` wiring'i ekle**

`src/dependencies.py` içindeki import satırını güncelle:

```python
from src.adapters.analysis.factory import build_analyzer, build_query_expander, build_question_answerer
```

`get_news_service` fonksiyonunu güncelle:

```python
def get_news_service(db: Session = Depends(get_db)) -> NewsService:
    repo = NewsRepository(db)
    analyzer = build_analyzer()
    search_repo = get_search_repository()
    query_expander = build_query_expander(get_cache())
    qa_port = build_question_answerer()
    return NewsService(
        repository=repo, analyzer=analyzer,
        search_repository=search_repo, query_expander=query_expander,
        qa_port=qa_port,
    )
```

- [ ] **Step 4: `news_router_v1.py`'a endpoint'i ekle**

Import satırını güncelle:

```python
from src.domain.schemas.news_schema import (
    NewsPage, NewsResponse, SearchRequest, SearchResult, TrendingResponse,
    RelatedResponse, StoryClusterResponse, AskRequest, RagAnswerResponse,
)
```

ve şu importu ekle (diğer importların yanına):

```python
from src.domain.ports.question_answering_port import QuestionAnsweringError
```

Dosyanın sonuna (`get_story_cluster_v1`'den sonra) ekle:

```python
@router.post("/news/ask", response_model=RagAnswerResponse)
@limiter.limit("10/minute")
def ask_question_v1(
    request: Request,
    body: AskRequest,
    user: Optional[User] = Depends(check_tier_limit),
    service: NewsService = Depends(get_news_service),
):
    """RAG tabanlı soru-cevap (roadmap #13) — kanıta dayalı, kanıt kapısı
    deterministik kodda çözülür, soru başına en fazla 1 Groq çağrısı (kanıt
    yoksa 0). Pro+ özelliği — her çağrı paylaşılan Groq kotasını tüketir,
    bu yüzden get_related'ın 60/minute'undan daha sıkı bir rate limit alır."""
    if not user or not tier_at_least(user_effective_tier(user), UserTier.PRO):
        raise HTTPException(
            status_code=403,
            detail="Soru-cevap asistanı Pro plan gerektirir. / The Q&A assistant requires a Pro plan.",
        )
    try:
        result = service.answer_question(
            body.question,
            article_id=body.article_id,
            history=[m.model_dump() for m in body.history],
        )
    except QuestionAnsweringError:
        raise HTTPException(
            status_code=503,
            detail="Şu an yanıt üretemiyorum, birazdan tekrar dene. / I can't answer right now, please try again shortly.",
        )
    if result is None:
        raise HTTPException(status_code=404, detail="Haber bulunamadı. / Article not found.")
    return result
```

- [ ] **Step 5: Testlerin geçtiğini doğrula**

Run: `venv\Scripts\python.exe -m pytest tests/adapters/test_ask_router.py -v`
Expected: 8 passed

- [ ] **Step 6: Tam backend test paketini çalıştır (regresyon)**

Run: `venv\Scripts\python.exe -m pytest tests/ -q`
Expected: hepsi yeşil

- [ ] **Step 7: Commit**

```bash
git add src/adapters/api/routers/v1/news_router_v1.py src/dependencies.py tests/adapters/test_ask_router.py
git commit -m "feat(rag): POST /api/v1/news/ask endpoint + DI wiring"
```

---

### Task 7: Frontend tipleri + API istemcisi

**Files:**
- Modify: `frontend/lib/types.ts`
- Modify: `frontend/lib/api.ts`

**Interfaces:**
- Produces: `AskMessage`, `RagSource`, `RagAnswerResponse` (TS interface'leri), `askQuestion(body: { question: string; article_id?: number | null; history: AskMessage[] }): Promise<RagAnswerResponse>`.

Bu dosyaların hiçbirinin dedike birim testi yok (proje konvansiyonu — Task 9'daki `npm run build` tip kontrolüyle doğrulanır).

- [ ] **Step 1: `types.ts`'e yeni tipleri ekle**

`frontend/lib/types.ts` dosyasının sonuna ekle:

```typescript
// v2.6 — RAG soru-cevap (roadmap #13).
export interface AskMessage {
  role: "user" | "assistant";
  content: string;
}

export interface RagSource {
  index: number;
  title: string;
  source: string;
  url: string;
}

export interface RagAnswerResponse {
  answer: string;
  coverage: "full" | "partial" | "none";
  corroboration_level: "single_source" | "multi_source" | "none";
  sources: RagSource[];
  suggest_alert: boolean;
}
```

- [ ] **Step 2: `api.ts`'e `askQuestion`'ı ekle**

`frontend/lib/api.ts` dosyasının başındaki type-only import bloğunu güncelle (mevcut listeye `AskMessage, RagAnswerResponse` ekle):

```typescript
import type {
  AccountUsage, AdminUserList, Article, AskMessage, BillingConfig, CheckoutResponse, MarketSnapshot, NewsPage,
  RagAnswerResponse, RelatedResponse, SearchResult, Sponsor, StoryClusterResponse, TrendingResponse, UsageRow, User,
} from "./types";
```

`fetchStoryCluster` fonksiyonundan sonra ekle:

```typescript
// v2.6 — RAG soru-cevap (roadmap #13). article_id null ise genel mod.
export async function askQuestion(body: {
  question: string;
  article_id?: number | null;
  history: AskMessage[];
}): Promise<RagAnswerResponse> {
  return req<RagAnswerResponse>(`${BASE}/api/v1/news/ask`, {
    method: "POST",
    body: JSON.stringify(body),
  });
}
```

- [ ] **Step 3: Tip kontrolü**

Run: `cd frontend; npx tsc --noEmit`
Expected: hata yok (frontend container ÇALIŞMIYORSA `npm run build` da kullanılabilir — CLAUDE.md gotcha'sına bak, container ayaktaysa SADECE `tsc --noEmit`)

- [ ] **Step 4: Commit**

```bash
git add frontend/lib/types.ts frontend/lib/api.ts
git commit -m "feat(rag): frontend AskMessage/RagAnswerResponse tipleri + askQuestion"
```

---

### Task 8: i18n sözlüğü

**Files:**
- Modify: `frontend/lib/i18n.ts`

**Interfaces:**
- Consumes: hiçbir şey.
- Produces: `UI.TR`/`UI.EN` içine yeni anahtarlar (aşağıdaki liste) — Task 10/11'in kullandığı `t.ask*` anahtarları.

- [ ] **Step 1: TR bloğuna ekle**

`newsletterKeywordAdd`/`newsletterKeywordRemove` satırından hemen sonra (ya da `storySources`/`hideSources`/`noSources` satırının yakınına, ilişkili özellik grubunda) ekle:

```typescript
    // ── RAG soru-cevap (roadmap #13) ──
    askNavLabel: "Soru Sor",
    askPageTitle: "Kanıta Dayalı Haber Asistanı",
    askPageDesc: "Takip ettiğimiz kaynaklara dayanarak soru sor — sadece elimizdeki kanıtı kullanır, uydurmaz.",
    askLocked: "Soru-cevap asistanı Pro plan gerektirir.",
    askPlaceholder: "Bir şey sor…",
    askSendBtn: "Gönder",
    askThinking: "Düşünüyor…",
    askEmptyState: "Henüz bir şey sormadın. Takip ettiğimiz haberler hakkında soru sorabilirsin.",
    askCoverageFull: "Tam kapsandı",
    askCoveragePartial: "Kısmen kapsandı",
    askCoverageNone: "Kanıt bulunamadı",
    askCorroborationMulti: "Birden fazla kaynak doğruluyor",
    askCorroborationSingle: "Tek kaynağa dayanıyor",
    askSuggestAlertBtn: "🔔 Bu konuda haber çıkarsa bildir",
    askErrorGeneric: "Şu an yanıt üretemiyorum, birazdan tekrar dene.",
    askBackToGeneral: "Genel sohbete dön",
    askSourcesLabel: "Kaynaklar:",
    askCardButton: "Sor",
```

- [ ] **Step 2: EN bloğuna ekle**

`newsletterKeywordAdd`/`newsletterKeywordRemove` satırının EN karşılığından hemen sonra ekle:

```typescript
    // ── RAG Q&A (roadmap #13) ──
    askNavLabel: "Ask",
    askPageTitle: "Evidence-Grounded News Assistant",
    askPageDesc: "Ask a question grounded in the sources we track — it only uses the evidence we have, never makes things up.",
    askLocked: "The Q&A assistant requires a Pro plan.",
    askPlaceholder: "Ask something…",
    askSendBtn: "Send",
    askThinking: "Thinking…",
    askEmptyState: "You haven't asked anything yet. Ask about the news we track.",
    askCoverageFull: "Fully covered",
    askCoveragePartial: "Partially covered",
    askCoverageNone: "No evidence found",
    askCorroborationMulti: "Confirmed by multiple sources",
    askCorroborationSingle: "Based on a single source",
    askSuggestAlertBtn: "🔔 Notify me if news breaks on this",
    askErrorGeneric: "I can't answer right now, please try again shortly.",
    askBackToGeneral: "Back to general chat",
    askSourcesLabel: "Sources:",
    askCardButton: "Ask",
```

- [ ] **Step 2: Tip kontrolü**

Run: `cd frontend; npx tsc --noEmit`
Expected: hata yok

- [ ] **Step 3: Commit**

```bash
git add frontend/lib/i18n.ts
git commit -m "feat(rag): frontend i18n anahtarları (TR+EN)"
```

---

### Task 9: `NewsCard`'a "💬 Sor" butonu

**Files:**
- Modify: `frontend/components/NewsCard.tsx`

**Interfaces:**
- Consumes: `useRouter` (zaten import edilmiş, `router.push` zaten kullanılıyor değil ama `next/navigation`'dan zaten import edilmiş durumda — satır 5), `t.askCardButton` (Task 8).
- Produces: Footer'da yeni bir `icon-chip` butonu, tıklanınca `/dashboard/ask?articleId=<id>`'e yönlendirir.

- [ ] **Step 1: `router` kullanımını doğrula**

`NewsCard.tsx`'te `const router = useRouter();` zaten satır 48'de tanımlı (`toggleSaved`/diğer aksiyonlar için kullanılmıyor olsa da import zaten mevcut — kontrol et, yoksa `useRouter` zaten satır 5'te import edilmiş, `const router = useRouter();`i component gövdesine ekle).

- [ ] **Step 2: Footer'a butonu ekle**

"Kaynaklar" butonundan hemen sonra, "Dinle" butonundan önce (`{canSpeak && (` satırından hemen önce) ekle:

```tsx
        <button onClick={() => router.push(`/dashboard/ask?articleId=${article.id}`)}
                className="icon-chip">
          <span className="icon-chip-glyph">💬</span> {t.askCardButton}
          {!isPro && (
            <span className="badge" style={{ background: "var(--accent-soft)", color: "var(--accent)",
                                              borderColor: "var(--accent-line)", fontSize: "0.6rem" }}>
              PRO
            </span>
          )}
        </button>
```

- [ ] **Step 3: Tip kontrolü**

Run: `cd frontend; npx tsc --noEmit`
Expected: hata yok

- [ ] **Step 4: Commit**

```bash
git add frontend/components/NewsCard.tsx
git commit -m "feat(rag): NewsCard'a habere özel soru-cevap butonu"
```

---

### Task 10: `/dashboard/ask` sayfası + nav linki

**Files:**
- Create: `frontend/app/dashboard/ask/page.tsx`
- Modify: `frontend/components/NavbarImpl.tsx`

**Interfaces:**
- Consumes: `askQuestion` (Task 7), `AskMessage`/`RagAnswerResponse` (Task 7), `UI`/`t.ask*` (Task 8), `useAuth`/`useSettings` (mevcut).
- Produces: `/dashboard/ask` sayfası — genel ve habere özel (`?articleId=N`) sohbet oturumlarını `Record<SessionId, ChatMessage[]>` React state'inde AYRI tutar; Navbar'da yeni "Soru Sor"/"Ask" linki.

- [ ] **Step 1: Sayfayı yaz**

```tsx
"use client";

// RAG soru-cevap sayfası (roadmap #13). Genel sohbet ile habere özel sohbet
// (?articleId=N) TAMAMEN ayrı state'lerde tutulur — sayfa yenilenince/kapanınca
// kaybolur (bilinçli karar, kalıcı sohbet geçmişi YOK, bkz. spec "Kapsam dışı").

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useSettings } from "@/lib/settings-context";
import { useAuth } from "@/lib/auth-context";
import { askQuestion, ApiError } from "@/lib/api";
import type { AskMessage, RagAnswerResponse } from "@/lib/types";
import { UI } from "@/lib/i18n";

type SessionId = "general" | `article:${number}`;

interface ChatMessage extends AskMessage {
  meta?: RagAnswerResponse;
}

export default function AskPage() {
  const { lang } = useSettings();
  const { user } = useAuth();
  const t = UI[lang];
  const et = user?.effective_tier ?? user?.tier;
  const isPro = et === "pro" || et === "enterprise";

  const [articleId, setArticleId] = useState<number | null>(null);
  const [sessions, setSessions] = useState<Record<string, ChatMessage[]>>({});
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const idParam = new URLSearchParams(window.location.search).get("articleId");
    setArticleId(idParam ? Number(idParam) : null);
  }, []);

  const sessionId: SessionId = articleId != null ? (`article:${articleId}` as const) : "general";
  const messages = sessions[sessionId] ?? [];

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages.length]);

  async function handleSend() {
    const question = input.trim();
    if (!question || busy) return;
    setInput("");
    setError("");
    const history = messages.map(({ role, content }) => ({ role, content }));
    const userMsg: ChatMessage = { role: "user", content: question };
    setSessions((cur) => ({ ...cur, [sessionId]: [...(cur[sessionId] ?? []), userMsg] }));
    setBusy(true);
    try {
      const res = await askQuestion({ question, article_id: articleId, history });
      const assistantMsg: ChatMessage = { role: "assistant", content: res.answer, meta: res };
      setSessions((cur) => ({ ...cur, [sessionId]: [...(cur[sessionId] ?? []), assistantMsg] }));
    } catch (err: unknown) {
      setError(err instanceof ApiError ? err.message : t.askErrorGeneric);
    } finally {
      setBusy(false);
    }
  }

  if (!isPro) {
    return (
      <div style={{ maxWidth: 640, margin: "60px auto", textAlign: "center" }}>
        <p style={{ color: "var(--text2)", marginBottom: 16 }}>{t.askLocked}</p>
        <Link href="/account" className="btn-primary">{t.liveUpgrade}</Link>
      </div>
    );
  }

  return (
    <div style={{ maxWidth: 720, margin: "0 auto", display: "flex", flexDirection: "column",
                  height: "calc(100vh - 140px)" }}>
      <div style={{ marginBottom: 16 }}>
        <p className="section-label" style={{ marginBottom: 8 }}>{t.askNavLabel}</p>
        <h1 style={{ fontSize: "1.6rem", fontWeight: 800, color: "var(--text)", letterSpacing: "-0.02em" }}>
          {t.askPageTitle}
        </h1>
        <p style={{ color: "var(--text3)", fontSize: "0.84rem" }}>{t.askPageDesc}</p>
        {articleId != null && (
          <Link href="/dashboard/ask" style={{ fontSize: "0.78rem", color: "var(--accent)", display: "inline-block", marginTop: 6 }}>
            ← {t.askBackToGeneral}
          </Link>
        )}
      </div>

      <div style={{ flex: 1, overflowY: "auto", display: "flex", flexDirection: "column", gap: 12, padding: "8px 0" }}>
        {messages.length === 0 && (
          <p style={{ color: "var(--text3)", textAlign: "center", marginTop: 40, fontSize: "0.88rem" }}>
            {t.askEmptyState}
          </p>
        )}
        {messages.map((m, i) => (
          <div key={i} style={{ alignSelf: m.role === "user" ? "flex-end" : "flex-start", maxWidth: "85%" }}>
            <div className="card-sm" style={{
              background: m.role === "user" ? "var(--accent-soft)" : "var(--surface)",
              borderRadius: 12, padding: "10px 14px",
            }}>
              <p style={{ fontSize: "0.88rem", color: "var(--text)", whiteSpace: "pre-wrap", lineHeight: 1.5, margin: 0 }}>
                {m.content}
              </p>
              {m.meta && (
                <div style={{ marginTop: 8, display: "flex", flexWrap: "wrap", gap: 6, alignItems: "center" }}>
                  <span className="badge" style={{
                    background: "var(--accent-soft)", color: "var(--accent)", borderColor: "var(--accent-line)",
                  }}>
                    {m.meta.coverage === "full" ? t.askCoverageFull
                      : m.meta.coverage === "partial" ? t.askCoveragePartial : t.askCoverageNone}
                  </span>
                  {m.meta.corroboration_level !== "none" && (
                    <span className="badge" style={{ background: "var(--surface)", color: "var(--text3)", borderColor: "var(--border)" }}>
                      {m.meta.corroboration_level === "multi_source" ? t.askCorroborationMulti : t.askCorroborationSingle}
                    </span>
                  )}
                </div>
              )}
              {m.meta && m.meta.sources.length > 0 && (
                <div style={{ marginTop: 8, fontSize: "0.78rem", color: "var(--text3)" }}>
                  {t.askSourcesLabel}{" "}
                  {m.meta.sources.map((s) => (
                    <a key={s.index} href={s.url} target="_blank" rel="noopener noreferrer"
                       style={{ color: "var(--accent)", marginRight: 8 }}>
                      [{s.index}] {s.source}
                    </a>
                  ))}
                </div>
              )}
              {m.meta?.suggest_alert && (
                <Link href={`/account?prefillKeyword=${encodeURIComponent(messages[i - 1]?.content ?? "")}`}
                      className="btn-secondary" style={{ marginTop: 8, fontSize: "0.78rem", display: "inline-block" }}>
                  {t.askSuggestAlertBtn}
                </Link>
              )}
            </div>
          </div>
        ))}
        <div ref={bottomRef} />
      </div>

      {error && <p style={{ color: "var(--neg)", fontSize: "0.82rem", marginTop: 8 }}>⚠ {error}</p>}

      <form onSubmit={(e) => { e.preventDefault(); handleSend(); }}
            style={{ display: "flex", gap: 8, marginTop: 12, paddingTop: 12, borderTop: "1px solid var(--border)" }}>
        <input value={input} onChange={(e) => setInput(e.target.value)}
               className="input" style={{ flex: 1, minWidth: 0 }} placeholder={t.askPlaceholder}
               disabled={busy} autoFocus />
        <button type="submit" disabled={busy || !input.trim()} className="btn-primary"
                style={{ whiteSpace: "nowrap", padding: "9px 20px" }}>
          {busy ? t.askThinking : t.askSendBtn}
        </button>
      </form>
    </div>
  );
}
```

- [ ] **Step 2: `ApiError`'ın `api.ts`'ten export edildiğini doğrula**

`frontend/lib/api.ts` içinde `export class ApiError extends Error` zaten mevcut (satır ~24) — yeni bir export gerekmez, sadece yukarıdaki sayfa import ettiği için mevcut export'un doğru isimle dışa açık olduğunu doğrula.

Run: `grep -n "export class ApiError" frontend/lib/api.ts`
Expected: 1 satır eşleşme

- [ ] **Step 3: Navbar'a nav linkini ekle**

`frontend/components/NavbarImpl.tsx` içindeki `navLinks` dizisini güncelle:

```typescript
  const navLinks = [
    { href: "/dashboard",        label: t.dashboard },
    { href: "/dashboard/search", label: t.search },
    { href: "/dashboard/ask",    label: t.askNavLabel },
    ...(user?.is_moderator ? [{ href: "/admin/users", label: t.admin }] : []),
  ];
```

- [ ] **Step 4: Tip kontrolü**

Run: `cd frontend; npx tsc --noEmit`
Expected: hata yok

- [ ] **Step 5: Commit**

```bash
git add frontend/app/dashboard/ask/page.tsx frontend/components/NavbarImpl.tsx
git commit -m "feat(rag): /dashboard/ask sayfası + nav linki"
```

---

### Task 11: `/account` sayfasında `prefillKeyword` desteği

**Files:**
- Modify: `frontend/app/account/page.tsx`

**Interfaces:**
- Consumes: `window.location.search` (mevcut sayfa zaten benzer bir deseni `dashboard/search/page.tsx`'te `?q=` için kullanıyor).
- Produces: `/account?prefillKeyword=<metin>` ile açılan sayfa, o metni bülten tercihleri bölümündeki anahtar kelime chip listesine (bu oturumun önceki görevinde eklenen chip UI, `nlKeywords: string[]`/`setNlKeywords`) otomatik ekler.

Task 10'daki "🔔 Bu konuda haber çıkarsa bildir" butonu bu query param'a yönlendiriyor — bu görev olmadan buton tıklanınca hiçbir görünür etki olmaz (spec'in "Bu konuda haber çıkınca haberdar et" bölümünün gerektirdiği karşı taraf).

- [ ] **Step 1: `fetchMyNewsletter` sonrası prefill mantığını ekle**

`frontend/app/account/page.tsx` içindeki mevcut `useEffect`i (satır ~76-90) güncelle:

```tsx
  useEffect(() => {
    loadUsage();
    fetchBillingConfig().then(setBilling).catch(() => {});
    fetchSources().then(setSources).catch(() => {});
    fetchSavedArticles().then(setSaved).catch(() => {});
    fetchMyNewsletter().then((prefs: NewsletterPrefs) => {
      setNlSubscribed(prefs.subscribed);
      let initialKeywords = prefs.subscribed ? (prefs.keywords ?? []) : [];
      if (prefs.subscribed) {
        setNlFrequency(prefs.frequency ?? "daily");
        setNlTopics(prefs.preferred_topics ?? []);
        setNlSources(prefs.preferred_sources ?? []);
      }
      // RAG "haberdar et" akışından ön-doldurma (roadmap #13, bkz. AskPage
      // suggest_alert) — mevcut listeye EKLENİR, üzerine yazmaz. Kullanıcı
      // yine de kendi "Kaydet"e basmalı, otomatik kayıt YAPILMAZ.
      const prefill = new URLSearchParams(window.location.search).get("prefillKeyword")?.trim();
      if (prefill && !initialKeywords.some((k) => k.toLowerCase() === prefill.toLowerCase())) {
        initialKeywords = [...initialKeywords, prefill];
      }
      setNlKeywords(initialKeywords);
    }).catch(() => {});
  }, [loadUsage]);
```

- [ ] **Step 2: Tip kontrolü**

Run: `cd frontend; npx tsc --noEmit`
Expected: hata yok

- [ ] **Step 3: Manuel doğrulama (dev server'da)**

`/account?prefillKeyword=deprem` adresini aç → bülten tercihleri bölümünde "deprem" chip'i otomatik görünmeli, "Kaydet"e basılmadan hiçbir şey kalıcı olmamalı.

- [ ] **Step 4: Commit**

```bash
git add frontend/app/account/page.tsx
git commit -m "feat(rag): /account prefillKeyword desteği (haberdar-et akışı)"
```

---

### Task 12: Frontend build doğrulaması

**Files:**
- (değişiklik yok — sadece doğrulama)

- [ ] **Step 1: Frontend container'ın ÇALIŞMADIĞINI doğrula**

Run: `docker ps --format "{{.Names}}: {{.Status}}" | grep -i frontend`
Expected: boş çıktı (container kapalıysa host'ta `npm run build` güvenlidir — CLAUDE.md gotcha'sına bak; container açıksa bu adımı atla, sadece `npx tsc --noEmit` yeterli)

- [ ] **Step 2: Prod build'i çalıştır**

Run: `cd frontend; npm run build`
Expected: `✓ Compiled successfully`, tip hatası yok, `/dashboard/ask` route listede görünür

- [ ] **Step 3: (Sadece build host'ta çalıştıysa) `.next`'i temizle**

Eğer geliştirme sırasında `docker compose up -d frontend` ile dev server'a geri dönülecekse:

Run: `docker compose stop frontend; rm -rf frontend/.next; docker compose start frontend` (sadece frontend container tekrar dev modda çalıştırılacaksa gerekli — CLAUDE.md "npm run build container ÇALIŞIRKEN" gotcha'sı)

- [ ] **Step 4: Commit gerekmez (sadece doğrulama adımı)**

---

### Task 13: Manuel/canlı QA + PR

**Files:**
- (kod değişikliği yok — doğrulama + entegrasyon)

Bu görev, spec'in "ZORUNLU canlı/manuel kalite doğrulaması" bölümünü ve bu oturumda alınan "session ayrımı Vitest yerine manuel QA ile doğrulanır" kararını uygular. Lokal `docker compose up -d` ile gerçek indexlenmiş haberlere karşı çalıştırılmalı (gerçek `GROQ_API_KEY` gerekir — CLAUDE.md'deki "local+prod aynı Groq key'i paylaşıyor" notuna göre kısa tut, sonrasında `docker compose down`).

- [ ] **Step 1: Lokal ortamı ayağa kaldır**

Run: `docker compose up -d`
Expected: `app`, `worker`, `frontend`, `chromadb`, `db` healthy (bkz. CLAUDE.md "Operasyonel notlar" — `/health` 200 dönene kadar polling ile bekle, tek istekle değil)

- [ ] **Step 2: Pro tier'lı bir test hesabıyla giriş yap, `/dashboard/ask`'a git**

- [ ] **Step 3: Senaryo 1 — Hiç haberi olmayan bir konu**

Örnek soru: "Beşiktaş'ın sağ kanat transferi ne durumda?" (ya da o an korpusta kesinlikle olmayan bir konu).
Expected: `coverage: "none"` + dürüst şablon cevap + "🔔 Bu konuda haber çıkarsa bildir" butonu görünür. `docker logs nexstream_app --tail 20` içinde bu istek için Groq çağrısı YAPILMADIĞINI doğrula (kanıt kapısı kapalıysa hiç log satırı olmamalı).

- [ ] **Step 4: Senaryo 2 — Tek kaynaklı, derin bir soru**

Bir fiyat/olay haberinin "nedeni" gibi tek kaynağın yüzeysel değindiği bir soru.
Expected: `coverage: "partial"`, model boşluğu DOLDURMUYOR, "Tek kaynağa dayanıyor" rozeti görünür.

- [ ] **Step 5: Senaryo 3 — Çok kaynaklı, iyi kapsanan bir konu**

Expected: `coverage: "full"` + "Birden fazla kaynak doğruluyor" rozeti + kaynaklar arası tutarlılık/ayrılık doğru sentezlenmiş.

- [ ] **Step 6: Senaryo 4 — Dolaylı-alakalı ama doğrudan olmayan bir soru**

Expected: model ilişkili gelişmeleri CEVAP GİBİ SUNMUYOR, `partial`/`none` arasında dürüst kalıyor.

- [ ] **Step 7: Senaryo 5 — Takip sorusu (multi-turn)**

Bir soru sor, cevabı aldıktan sonra "peki ya X'te?" gibi önceki bağlama referans veren ikinci bir soru sor.
Expected: History doğru taşınıyor, ikinci cevap ilk sorunun bağlamını biliyor.

- [ ] **Step 8: Session ayrımı (bu oturumda Vitest yerine manuel QA'ya taşındı)**

Genel sohbette birkaç mesaj gönder → bir haber kartından "💬 Sor"a tıkla (habere özel sohbete geç) → orada mesaj gönder → nav'dan "Soru Sor"a tıklayarak genel sohbete dön.
Expected: genel sohbetin geçmişi KORUNMUŞ (kaybolmamış), habere özel sohbetin geçmişi genel sohbette GÖRÜNMÜYOR. Aynı karta tekrar tıklanınca habere özel geçmiş GERİ GELİYOR (state'te durduğu için).

- [ ] **Step 9: Free tier kullanıcıyla kilit ekranını doğrula**

Free hesapla `/dashboard/ask`'a git → `askLocked` mesajı + "Yükselt" butonu görünmeli, form hiç render edilmemeli.

- [ ] **Step 10: `RETRIEVAL_THRESHOLD` kalibrasyonu (gerekirse)**

Senaryo 1-4'ün sonuçları beklentiyle uyuşmuyorsa (ör. Senaryo 1'de yine de Groq çağrılıyor, ya da Senaryo 3'te gerçekten ilgili bir haber "none" dönüyor), `src/infrastructure/config/settings.py::rag_retrieval_threshold` değerini ayarla (varsayılan 0.5), testleri tekrar çalıştır, commit et.

- [ ] **Step 11: `docker compose down` (paylaşılan Groq kotasını korumak için)**

Run: `docker compose down`

- [ ] **Step 12: PR aç**

```bash
git checkout -b feat/rag-soru-cevap
git push -u origin feat/rag-soru-cevap
gh pr create --title "feat: RAG tabanlı soru-cevap (roadmap #13)" --body "Spec: docs/superpowers/specs/2026-08-26-rag-soru-cevap-design.md
Plan: docs/superpowers/plans/2026-08-26-rag-soru-cevap.md

Kanıt kapısı deterministik kodda çözülür, soru başına en fazla 1 Groq çağrısı (kanıt yoksa 0). Pro+ gated, /api/v1/news/ask (kota sayacına dahil). Genel + habere özel iki ayrı sohbet oturumu (frontend state, kalıcı saklama yok).

Manuel QA: 5 senaryo + session ayrımı + free-tier kilit ekranı doğrulandı (bkz. plan Task 12)."
```

- [ ] **Step 13: CI'nin geçmesini bekle, merge et**

Run: `gh pr checks <PR#> --watch`
Expected: `test`, `frontend`, `security-audit` yeşil

```bash
gh pr merge <PR#> --squash --delete-branch
git fetch origin && git reset --hard origin/main
```

(son satır, önceki oturumda öğrenilen gotcha'yı önler — bkz. CLAUDE.md/session geçmişi: `gh pr merge` bazen yerel `main`'i fast-forward edemiyor, diskteki dosyalar eski hâle dönebilir.)

- [ ] **Step 14: Otomatik deploy'u doğrula**

Run: `gh run list --branch main --limit 1` sonra `gh run watch <run-id> --exit-status`
Expected: `test`+`frontend`+`security-audit`+`Deploy to production (SSM)` hepsi yeşil, health check dahil.
