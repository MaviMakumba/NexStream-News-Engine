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
