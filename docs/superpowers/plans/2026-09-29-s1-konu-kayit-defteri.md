# S1 — Konu Kayıt Defteri Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Haber konularını (12 konu: mevcut 8 + Science, Crypto, Environment, Entertainment) tek bir backend kayıt defterinde topla; analiz prompt'u, e-posta etiketleri, frontend filtre/bülten listeleri ve API bu tek kaynaktan türesin.

**Architecture:** `src/domain/topics.py` (saf domain, bağımlılıksız) konu kimliği + TR/EN etiket + prompt ipucunu tutar. Analiz adapter'ı (`common.py`) prompt'u ve geçerlilik kümesini, e-posta adapter'ı etiketleri oradan alır. Frontend için `scripts/gen_frontend_topics.py` `frontend/lib/topics.ts` üretir; bir senkron testi üretilen dosya ile kayıt defteri arasındaki kaymayı yakalar (çalışma zamanı API çağrısı YOK). Ayrıca dış tüketiciler için `GET /api/v1/news/topics` eklenir.

**Tech Stack:** Python 3.13 / FastAPI / pytest, Next.js 16 + TypeScript, Playwright mobil regresyon paketi (ayrı dalda, #172).

**Spec:** `docs/superpowers/specs/2026-09-29-icerik-genisletme-cok-dillilik-tazelik-design.md` §4.1 (S1).

**Spec'ten bilinçli sapma:** §4.1 frontend'in konu listesini `GET /api/v1/news/topics`'ten okumasını söylüyordu. Bu plan bunun yerine **üretilen statik dosya + senkron testi** kullanır, çünkü (a) `/api/v1/*` her çağrı kullanıcının günlük kotasından yer (Free = 100/gün), (b) dashboard'un ilk boyaması ağa bağımlı olmasın, (c) hata modu (uç yanıt vermezse filtre boş) tamamen kalkar. Uç dış API tüketicileri için yine eklenir.

## Global Constraints

- Konu **kimlikleri** İngilizce sabit değerlerdir ve değişmez (`Technology`, `Sports`, `Economy`, `Politics`, `Health`, `Culture`, `World`, `Science`, `Crypto`, `Environment`, `Entertainment`, `Other`); DB'deki eski haberler bu kimlikleri kullanır. Migration YOK.
- Bilinmeyen konu (model uydurursa) → `Other`. Etiketi olmayan kimlik UI/e-postada kimliğin kendisiyle gösterilir (asla boş/çökme).
- Kural: i18n'de `if language == "TR" else` YASAK — etiketler sözlük (`labels: {"TR":..., "EN":...}`).
- Analiz prompt şablonu (makale metni hariç) **1000 karakter** altında kalır (bugün 767; test tavanı 850'den bilinçli olarak yükseltilir).
- `src/domain/*` hiçbir `adapters/`/`application/` import etmez.
- Merge yok: dal `feat/s1-topic-registry`, PR açılır, sonda tek deploy.

## Review Focus

- Modelin geçersiz/uydurma konu üretmesi (`"Finance"`, `"crypto"` küçük harf, `None`) → `Other`, çökme yok (Task 2 testi).
- **Eski** konu değerli haberler (`Technology` …) yeni sistemde etiketleniyor; kayıt defterinde olmayan bir değer (`"Crime"` — eski testlerde geçiyor) ham haliyle gösteriliyor (Task 3 testi).
- Abone `preferred_topics` içinde yeni konu (`Crypto`) bulunca eşleştirme çalışıyor; kayıt defterinde olmayan eski/uydurma değer sessizce yok sayılmıyor ama hata da vermiyor (Task 1 testi).
- Frontend listesi backend'den kayarsa CI kırmızı olmalı (Task 5 testi).
- Prompt'un 5 ipucu satırı token bütçesini şişirmemeli (Task 2 bütçe testi).

## File Structure

| Dosya | Sorumluluk |
|---|---|
| Create `src/domain/topics.py` | Konu kayıt defteri: `Topic`, `TOPICS`, `VALID_TOPIC_IDS`, `topic_label()`, `normalize_topic()` |
| Modify `src/adapters/analysis/common.py` | Prompt konu satırı + `VALID_TOPICS` kayıt defterinden |
| Modify `src/adapters/notifications/email_adapter.py` | `_TOPIC_LABELS` sözlüğü yerine `topic_label()` |
| Modify `src/adapters/api/routers/v1/news_router_v1.py` | `GET /api/v1/news/topics` |
| Create `scripts/gen_frontend_topics.py` | `frontend/lib/topics.ts` üretici |
| Create `frontend/lib/topics.ts` | ÜRETİLEN dosya (elle düzenlenmez) |
| Modify `frontend/lib/i18n.ts`, `frontend/app/dashboard/page.tsx`, `frontend/app/account/page.tsx` | Elle listeler yerine `TOPICS` |
| Create tests | `tests/domain/test_topics.py`, `tests/infrastructure/test_frontend_topics_sync.py` + mevcut test dosyalarına eklemeler |

---

### Task 1: Domain kayıt defteri

**Files:**
- Create: `src/domain/topics.py`
- Test: `tests/domain/test_topics.py`

**Interfaces:**
- Produces: `Topic(id: str, labels: Dict[str, str], hint: str = "")` (frozen dataclass); `TOPICS: Tuple[Topic, ...]`; `VALID_TOPIC_IDS: FrozenSet[str]`; `topic_label(topic_id: str, language: str, fallback_language: str = "EN") -> str`; `normalize_topic(value: object) -> str` (geçersiz → `"Other"`).

- [ ] **Step 1: Write the failing test** — `tests/domain/test_topics.py`

```python
from src.domain.models.article import Article
from src.domain.models.subscriber import Subscriber
from src.domain.services.subscriber_matching import article_matches_subscriber
from src.domain.topics import TOPICS, VALID_TOPIC_IDS, normalize_topic, topic_label


def test_registry_has_twelve_topics_with_stable_ids_and_other_last():
    ids = [t.id for t in TOPICS]
    assert ids == ["Technology", "Sports", "Economy", "Politics", "Health", "Culture", "World",
                   "Science", "Crypto", "Environment", "Entertainment", "Other"]
    assert VALID_TOPIC_IDS == frozenset(ids)


def test_every_topic_has_tr_and_en_labels():
    for t in TOPICS:
        assert t.labels["TR"] and t.labels["EN"], t.id


def test_topic_label_uses_requested_language_and_falls_back():
    assert topic_label("Science", "TR") == "Bilim"
    assert topic_label("Environment", "EN") == "Environment & Climate"
    assert topic_label("Crypto", "DE") == "Crypto"          # bilinmeyen dil → fallback (EN)
    assert topic_label("Crime", "TR") == "Crime"            # kayıt defterinde olmayan → ham kimlik
    assert topic_label("", "TR") == ""


def test_normalize_topic_maps_anything_invalid_to_other():
    assert normalize_topic("Crypto") == "Crypto"
    for bad in ("Finance", "crypto", "", None, 5, ["Sports"]):
        assert normalize_topic(bad) == "Other"


def test_new_topic_works_in_subscriber_matching():
    art = Article(title="Bitcoin yükseldi", source="CoinDesk", url="u", content="c")
    art.topic = "Crypto"
    assert article_matches_subscriber(art, Subscriber(email="a@b.c", preferred_topics=["Crypto"])) is True
    assert article_matches_subscriber(art, Subscriber(email="a@b.c", preferred_topics=["Sports"])) is False
```

- [ ] **Step 2: Run** `venv\Scripts\python.exe -m pytest tests/domain/test_topics.py -q` → Expected: FAIL (`ModuleNotFoundError: src.domain.topics`).

- [ ] **Step 3: Write minimal implementation** — `src/domain/topics.py`

```python
"""Haber konuları için TEK doğruluk kaynağı (29 Eylül 2026, S1).

Eskiden aynı liste 5+ yerde elle kopyalanıyordu (analiz prompt'u, e-posta
etiketleri, frontend filtre/bülten/etiket sözlükleri). Buraya yeni bir konu
eklemek = `TOPICS`'a bir `Topic` satırı + `python scripts/gen_frontend_topics.py`.

Kimlikler (`Topic.id`) İngilizce sabit değerlerdir ve DB'de bu haliyle saklanır —
ASLA yeniden adlandırma. Etiketler dil sözlüğüdür (yeni dil = anahtar eklemek).
`hint`: yalnızca birbirine karışan konular için analiz prompt'una giren kısa ipucu
(her karakter her Groq çağrısında tekrarlanır → kısa tut).
"""

from dataclasses import dataclass, field
from typing import Dict, FrozenSet, Tuple


@dataclass(frozen=True)
class Topic:
    id: str
    labels: Dict[str, str] = field(default_factory=dict)
    hint: str = ""


TOPICS: Tuple[Topic, ...] = (
    Topic("Technology", {"TR": "Teknoloji", "EN": "Technology"}),
    Topic("Sports", {"TR": "Spor", "EN": "Sports"}),
    Topic("Economy", {"TR": "Ekonomi", "EN": "Economy"}, "markets, business, not crypto"),
    Topic("Politics", {"TR": "Siyaset", "EN": "Politics"}),
    Topic("Health", {"TR": "Sağlık", "EN": "Health"}),
    Topic("Culture", {"TR": "Kültür", "EN": "Culture"}, "arts, literature, history"),
    Topic("World", {"TR": "Dünya", "EN": "World"}),
    Topic("Science", {"TR": "Bilim", "EN": "Science"}, "research, space"),
    Topic("Crypto", {"TR": "Kripto", "EN": "Crypto"}, "cryptocurrency, blockchain"),
    Topic("Environment", {"TR": "Çevre & İklim", "EN": "Environment & Climate"}, "climate, nature"),
    Topic("Entertainment", {"TR": "Eğlence", "EN": "Entertainment"}, "celebrities, film, music, TV"),
    Topic("Other", {"TR": "Diğer", "EN": "Other"}),
)

VALID_TOPIC_IDS: FrozenSet[str] = frozenset(t.id for t in TOPICS)
_BY_ID: Dict[str, Topic] = {t.id: t for t in TOPICS}


def topic_label(topic_id: str, language: str, fallback_language: str = "EN") -> str:
    """Konu etiketi. Bilinmeyen dil → `fallback_language`; kayıt defterinde olmayan
    kimlik → kimliğin kendisi (UI/e-posta asla boş kalmaz)."""
    if not topic_id:
        return ""
    topic = _BY_ID.get(topic_id)
    if topic is None:
        return topic_id
    return topic.labels.get(language) or topic.labels.get(fallback_language) or topic_id


def normalize_topic(value: object) -> str:
    """Model çıktısını geçerli bir konu kimliğine indirger; geçersiz her şey → 'Other'."""
    return value if isinstance(value, str) and value in VALID_TOPIC_IDS else "Other"
```

- [ ] **Step 4: Run** `venv\Scripts\python.exe -m pytest tests/domain/test_topics.py -q` → Expected: PASS (5 test).

- [ ] **Step 5: Commit**

```bash
git add src/domain/topics.py tests/domain/test_topics.py
git commit -m "feat(topics): konu kayit defteri (12 konu, TR/EN etiket, prompt ipucu)"
```

---

### Task 2: Analiz prompt'u ve ayrıştırıcı kayıt defterinden

**Files:**
- Modify: `src/adapters/analysis/common.py:18` (`VALID_TOPICS`), `:27` (prompt topic satırı), `:59-61` (`parse_analysis_json`)
- Test: `tests/adapters/test_analysis_common.py`, `tests/adapters/test_ner_prompt.py`

**Interfaces:**
- Consumes: `TOPICS`, `VALID_TOPIC_IDS`, `normalize_topic` (Task 1).
- Produces: `VALID_TOPICS` (geriye uyumlu ad, artık `VALID_TOPIC_IDS`); `build_analysis_prompt` yeni konu satırı.

- [ ] **Step 1: Write the failing tests**

`tests/adapters/test_analysis_common.py` — dosyanın sonuna ekle ve `_TEMPLATE_ONLY_CHAR_BUDGET = 850` satırını `1000` yap, üstündeki yorumun sonuna `# 29 Eyl 2026 (S1): 4 yeni konu + 5 kısa ipucu için 850 → 1000.` ekle:

```python
def test_prompt_lists_every_registered_topic_and_hints():
    from src.domain.topics import TOPICS
    prompt = build_analysis_prompt("")
    for t in TOPICS:
        assert t.id in prompt, t.id
        if t.hint:
            assert t.hint in prompt, t.id
```

`tests/adapters/test_ner_prompt.py` — `test_all_valid_topics_accepted` içindeki elle `valid_topics` listesini şununla değiştir:

```python
    from src.domain.topics import TOPICS
    valid_topics = [t.id for t in TOPICS]
```

ve dosya sonuna ekle:

```python
def test_model_invented_topic_variants_fall_back_to_other():
    """'Finance', küçük harf 'crypto', boş ya da sayı → 'Other' (çökme yok)."""
    import json as _json
    from src.adapters.analysis.common import parse_analysis_json
    for bad in ("Finance", "crypto", "", None, 7):
        raw = _json.dumps({"sentiment_score": 0.0, "summary": "s", "entities": {}, "topic": bad})
        assert parse_analysis_json(raw, "t")["topic"] == "Other", repr(bad)
```

- [ ] **Step 2: Run** `venv\Scripts\python.exe -m pytest tests/adapters/test_analysis_common.py tests/adapters/test_ner_prompt.py -q` → Expected: FAIL (yeni konular prompt'ta yok; `Science` reddediliyor).

- [ ] **Step 3: Implement** — `src/adapters/analysis/common.py`

`VALID_TOPICS = {...}` satırını şununla değiştir:

```python
from src.domain.topics import TOPICS, VALID_TOPIC_IDS, normalize_topic

VALID_TOPICS = VALID_TOPIC_IDS   # geriye uyumlu ad


def _topic_prompt_line() -> str:
    """'Technology, Sports, Economy (markets, business, not crypto), ...' — ipucu yalnız karışan konularda."""
    return ", ".join(f"{t.id} ({t.hint})" if t.hint else t.id for t in TOPICS)


_TOPIC_LINE = _topic_prompt_line()
```

Prompt şablonunda `- topic: one of Technology, Sports, Economy, Politics, Health, Culture, World, Other` satırını f-string içinde şuna çevir: `- topic: one of {_TOPIC_LINE}`.

`parse_analysis_json` içindeki

```python
    topic = result.get("topic", "Other")
    if topic not in VALID_TOPICS:
        topic = "Other"
```

bloğunu şununla değiştir:

```python
    topic = normalize_topic(result.get("topic", "Other"))
```

- [ ] **Step 4: Run** aynı komut + tam paket `venv\Scripts\python.exe -m pytest tests -q` → Expected: PASS. Bütçe testi geçmiyorsa ipucu metinlerini kısalt (tavan 1000 karakter; hedef ≈ 930).

- [ ] **Step 5: Commit**

```bash
git add src/adapters/analysis/common.py tests/adapters/test_analysis_common.py tests/adapters/test_ner_prompt.py
git commit -m "feat(analysis): prompt konu listesi ve gecerlilik kayit defterinden (12 konu)"
```

---

### Task 3: E-posta etiketleri kayıt defterinden

**Files:**
- Modify: `src/adapters/notifications/email_adapter.py:96-110` (`_TOPIC_LABELS`), `:141-146` (`_topic_label`)
- Test: `tests/adapters/test_email_adapter.py`

**Interfaces:**
- Consumes: `topic_label` (Task 1).

- [ ] **Step 1: Write the failing test** — `tests/adapters/test_email_adapter.py` sonuna:

```python
def test_topic_label_new_and_legacy_topics():
    from src.adapters.notifications.email_adapter import _topic_label
    assert _topic_label("Crypto", "TR") == "Kripto"
    assert _topic_label("Environment", "EN") == "Environment & Climate"
    assert _topic_label("Sports", "TR") == "Spor"           # eski konu bozulmadı
    assert _topic_label("Crime", "TR") == "Crime"           # kayıt defterinde olmayan → ham
    assert _topic_label("", "TR") == ""
    assert _topic_label("Science", "DE") == "Science"       # bilinmeyen dil → varsayılan dil
```

- [ ] **Step 2: Run** `venv\Scripts\python.exe -m pytest tests/adapters/test_email_adapter.py -q -k topic_label` → Expected: FAIL (`Crypto` etiketi yok).

- [ ] **Step 3: Implement** — `_TOPIC_LABELS` sözlüğünü ve onu açıklayan yorumu sil; import ekle ve fonksiyonu değiştir:

```python
from src.domain.topics import topic_label

def _topic_label(topic: str, language: str) -> str:
    if not topic:
        return ""
    return topic_label(topic, language, fallback_language=_DEFAULT_LANG)
```

(`_DEFAULT_LANG` dosyada zaten tanımlı.)

- [ ] **Step 4: Run** `venv\Scripts\python.exe -m pytest tests -q` → Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/adapters/notifications/email_adapter.py tests/adapters/test_email_adapter.py
git commit -m "refactor(email): konu etiketleri kayit defterinden"
```

---

### Task 4: `GET /api/v1/news/topics`

**Files:**
- Modify: `src/adapters/api/routers/v1/news_router_v1.py` (`/news/sources` yakınına)
- Test: `tests/adapters/test_v1_news_router.py`

**Interfaces:**
- Consumes: `TOPICS` (Task 1).
- Produces: `[{"id": str, "labels": {"TR": str, "EN": str}}, ...]`, kayıt defteri sırasıyla.

- [ ] **Step 1: Write the failing test** — `tests/adapters/test_v1_news_router.py` sonuna:

```python
def test_v1_topics_lists_registry_in_order(app_client):
    r = app_client.get("/api/v1/news/topics")
    assert r.status_code == 200
    data = r.json()
    assert [t["id"] for t in data][:2] == ["Technology", "Sports"]
    assert data[-1]["id"] == "Other"
    assert {"id": "Crypto", "labels": {"TR": "Kripto", "EN": "Crypto"}} in data
    assert len(data) == 12
```

- [ ] **Step 2: Run** `venv\Scripts\python.exe -m pytest tests/adapters/test_v1_news_router.py -q -k topics` → Expected: FAIL (404).

- [ ] **Step 3: Implement** — `news_router_v1.py`'ye import `from src.domain.topics import TOPICS` ve `get_sources_v1` benzeri uçtan sonra:

```python
@router.get("/news/topics")
@limiter.limit("60/minute")
def get_topics_v1(request: Request):
    """Geçerli konu kimlikleri + TR/EN etiketleri (filtre `topic=` değerleri)."""
    return [{"id": t.id, "labels": dict(t.labels)} for t in TOPICS]
```

Rota, `/news/{article_id}/...` parametreli rotalardan ÖNCE tanımlı olmalı (sources/trending ile aynı bölgede).

- [ ] **Step 4: Run** `venv\Scripts\python.exe -m pytest tests -q` → Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/adapters/api/routers/v1/news_router_v1.py tests/adapters/test_v1_news_router.py
git commit -m "feat(api): GET /api/v1/news/topics"
```

---

### Task 5: Frontend — üretilen liste + senkron testi

**Files:**
- Create: `scripts/gen_frontend_topics.py`, `frontend/lib/topics.ts` (üretilir), `tests/infrastructure/test_frontend_topics_sync.py`
- Modify: `frontend/lib/i18n.ts:3-17`, `frontend/app/dashboard/page.tsx:22`, `frontend/app/account/page.tsx:26`

**Interfaces:**
- Consumes: `TOPICS` (Task 1).
- Produces: `render() -> str` (script), `TOPICS`, `TopicId` (`frontend/lib/topics.ts`).

- [ ] **Step 1: Write the failing test** — `tests/infrastructure/test_frontend_topics_sync.py`

```python
"""frontend/lib/topics.ts ÜRETİLEN bir dosyadır; kayıt defteriyle kayarsa CI kırmızı olmalı."""
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _render() -> str:
    spec = importlib.util.spec_from_file_location("gen_frontend_topics", ROOT / "scripts" / "gen_frontend_topics.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.render()


def test_generated_frontend_topics_match_registry():
    actual = (ROOT / "frontend" / "lib" / "topics.ts").read_text(encoding="utf-8").replace("\r\n", "\n")
    assert actual == _render(), "frontend/lib/topics.ts eski — çalıştır: python scripts/gen_frontend_topics.py"
```

- [ ] **Step 2: Run** `venv\Scripts\python.exe -m pytest tests/infrastructure/test_frontend_topics_sync.py -q` → Expected: FAIL (script yok).

- [ ] **Step 3: Implement**

`scripts/gen_frontend_topics.py`:

```python
"""frontend/lib/topics.ts dosyasını src/domain/topics.py kayıt defterinden üretir.

Çalıştır: python scripts/gen_frontend_topics.py
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.domain.topics import TOPICS  # noqa: E402

OUT = ROOT / "frontend" / "lib" / "topics.ts"


def render() -> str:
    rows = ",\n".join(
        f"  {{ id: {json.dumps(t.id)}, labels: {json.dumps(t.labels, ensure_ascii=False)} }}" for t in TOPICS
    )
    return (
        "// ÜRETİLDİ — ELLE DÜZENLEME. Kaynak: src/domain/topics.py\n"
        "// Yeniden üret: python scripts/gen_frontend_topics.py (tests/infrastructure/test_frontend_topics_sync.py kaymayı yakalar)\n"
        f"export const TOPICS = [\n{rows},\n] as const;\n\n"
        'export type TopicId = (typeof TOPICS)[number]["id"];\n'
    )


if __name__ == "__main__":
    OUT.write_text(render(), encoding="utf-8", newline="\n")
    print(f"yazıldı: {OUT}")
```

Sonra `python scripts/gen_frontend_topics.py` çalıştır. Ardından:

- `frontend/lib/i18n.ts` — `TOPIC_LABELS` literalini şununla değiştir (dosyanın başındaki `import type { Lang }` satırının altına `import { TOPICS } from "./topics";` ekle):

```ts
const ALL_TOPICS_LABEL: Record<string, string> = { TR: "Tüm Konular", EN: "All Topics" };

export const TOPIC_LABELS: Record<string, Record<string, string>> = Object.fromEntries(
  Object.keys(ALL_TOPICS_LABEL).map((lang) => [
    lang,
    { "": ALL_TOPICS_LABEL[lang], ...Object.fromEntries(TOPICS.map((t) => [t.id, t.labels[lang as "TR" | "EN"]])) },
  ]),
);
```

- `frontend/app/dashboard/page.tsx:22` → `const TOPIC_VALUES    = ["", ...TOPICS.map((t) => t.id)];` ve import `import { TOPICS } from "@/lib/topics";`
- `frontend/app/account/page.tsx:26` → `const NEWSLETTER_TOPICS = TOPICS.map((t) => t.id);` ve aynı import.

- [ ] **Step 4: Run** `venv\Scripts\python.exe -m pytest tests -q` ve `cd frontend; npx tsc --noEmit; npm run test:unit` → Expected: hepsi PASS/temiz.

- [ ] **Step 5: Commit**

```bash
git add scripts/gen_frontend_topics.py frontend/lib/topics.ts frontend/lib/i18n.ts frontend/app/dashboard/page.tsx frontend/app/account/page.tsx tests/infrastructure/test_frontend_topics_sync.py
git commit -m "feat(frontend): konu listeleri kayit defterinden uretilen topics.ts (senkron testli)"
```

---

### Task 6: Belgeler, doğrulama, PR

**Files:**
- Modify: `CLAUDE.md` (BİLİNEN NOTLAR'a 1 madde), `docs/CHANGELOG.md`

- [ ] **Step 1: CLAUDE.md**'ye kalıcı kural ekle: "Yeni bir haber konusu = `src/domain/topics.py::TOPICS`'a satır + `python scripts/gen_frontend_topics.py`; başka hiçbir yerde konu listesi tutma (senkron testi kırılır). Konu kimlikleri DB'de olduğu için asla yeniden adlandırılmaz."
- [ ] **Step 2: CHANGELOG** "29 Eylül 2026" bölümüne S1 girişi (12 konu, tek kaynak, prompt bütçesi 850→1000, frontend statik üretim gerekçesi, prod'da yapılacak: hiçbir migration yok).
- [ ] **Step 3: Tam doğrulama** — `venv\Scripts\python.exe -m pytest tests -q` (hepsi yeşil), `cd frontend; npx tsc --noEmit; npm run build` (build sonrası `rm -rf .next`).
- [ ] **Step 4: Gerçek prompt duman testi (küçük, ~5 Groq çağrısı):** 5 örnek başlık (kripto, bilim, iklim, magazin, ekonomi) ile `GroqAnalyzer().analyze_text` çağır; konuların beklenen kimliğe düştüğünü ve JSON'un geçerli olduğunu gözle doğrula (yanlış sınıflarsa ipuçlarını güncelle). Local `.env` GROQ anahtarı prod ile paylaşımlı — 5 çağrı ihmal edilebilir.
- [ ] **Step 5: Commit + push + PR** (`gh pr create`, merge YOK).

```bash
git add CLAUDE.md docs/CHANGELOG.md
git commit -m "docs: S1 konu kayit defteri (CLAUDE.md kurali + CHANGELOG)"
git push -u origin feat/s1-topic-registry
gh pr create --base main --title "feat(S1): konu kayit defteri - 12 konu tek kaynak" --body "Spec §4.1. Detay: docs/superpowers/plans/2026-09-29-s1-konu-kayit-defteri.md"
```

---

## Self-Review

**Spec coverage (§4.1):** kayıt defteri ✓ (T1), prompt + geçerlilik ✓ (T2), e-posta etiketleri ✓ (T3), `GET /api/v1/news/topics` ✓ (T4), frontend tek kaynak ✓ (T5, statik üretimle — sapma yukarıda gerekçeli), eski haberler eski konusuyla kalır ✓ (Global Constraints; migration yok), abone `preferred_topics` şema değişmez ✓ (T1 testi). §4.1'in "ipuçları" ✓ (Topic.hint). Gap yok.

**Placeholder taraması:** yok. **Tip tutarlılığı:** `topic_label(topic_id, language, fallback_language)` T1'de tanımlı, T3'te aynı imzayla çağrılıyor; `normalize_topic` T1→T2 aynı ad; `VALID_TOPICS` alias T2'de korunuyor (mevcut import eden kod kırılmaz); `TOPICS` (Python) ↔ `TOPICS` (TS) aynı ad, farklı dil.

**Review Focus:** 5 satırın 5'i bir task testine bağlandı (T2 uydurma konu + bütçe, T3 eski/bilinmeyen etiket, T1 abone eşleşmesi, T5 senkron).
