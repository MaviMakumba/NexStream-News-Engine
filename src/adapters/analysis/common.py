"""Analyzer'lar arası paylaşılan prompt + JSON ayrıştırma + nötr fallback.

Groq ve HuggingFace analyzer'ları aynı sözleşmeyi üretsin diye tek noktadan beslenir.

31 Ağu 2026 (roadmap #25, TPD maliyeti düşürme): şablon metni ~278 token'dan
~192 token'a sıkıştırıldı — aynı alan sözleşmesi, aynı sentiment kalibrasyon
örnekleri (breakthrough/victory, disaster/death/crisis vb.), sadece madde
işaretleri ve tekrarlayan kelimeler kırpıldı. Bu, makale içeriğinden BAĞIMSIZ
sabit ek yük olduğu için her tek Groq çağrısında garanti tasarruf — haber
başına ~86 token, günlük ~206 haber hacminde ~%9 TPD kazancı (bkz. CLAUDE.md
BİLİNEN NOTLAR "TPD kotası" notu). Daha fazla sıkıştırma denenmedi: JSON
şema uyumunun bozulma riski (yeniden deneme = daha FAZLA token) kazancı
aşabilir, bu yüzden bilinçli olarak dengeli bir noktada durduruldu.
"""
import json
import re

from src.domain.topics import TOPICS, normalize_topic

def _topic_prompt_line() -> str:
    """'Technology, Economy (markets, business, not crypto), ...' — ipucu yalnız karışan konularda."""
    return ", ".join(f"{t.id} ({t.hint})" if t.hint else t.id for t in TOPICS)


_TOPIC_LINE = _topic_prompt_line()


def build_analysis_prompt(text: str) -> str:
    return f"""Analyze this news article (English or Turkish). Return ONLY valid JSON:
- sentiment_score: float -1.0 to 1.0. Use the FULL range: 0.7-1.0 strong positive (breakthrough/victory/success), 0.3-0.7 mild positive (improvement/progress), -0.2-0.2 neutral (factual/routine), -0.3 to -0.7 mild negative (concern/decline/conflict), -0.7 to -1.0 strong negative (disaster/death/crisis).
- sentiment_label: "Positive" if score>0.2, "Negative" if score<-0.2, else "Neutral"
- summary: 1-2 sentence summary, same language as the article
- entities: object with persons/organizations/locations arrays — named entities mentioned, empty arrays OK
- topic: one of {_TOPIC_LINE}

Article:
{text[:1000]}

JSON only, no markdown, no explanation."""


def sentiment_label_for(score: float) -> str:
    """Etiket skorun saf fonksiyonu (prompt sözleşmesiyle aynı eşikler). Modelin
    yazdığı etiket metnine güvenilmez: qwen 'Strongly Negative' üretebiliyor,
    UI/filtre/API deseni yalnızca Positive|Negative|Neutral biliyor."""
    if score > 0.2:
        return "Positive"
    if score < -0.2:
        return "Negative"
    return "Neutral"


def parse_analysis_json(content: str, text: str) -> dict:
    """Model çıktısını standart analiz sözleşmesine çevirir. Geçersiz JSON'da JSONDecodeError fırlatır."""
    content = re.sub(r"```json|```", "", content).strip()
    result = json.loads(content)

    entities = result.get("entities", {})
    if not isinstance(entities, dict):
        entities = {}
    for key in ("persons", "organizations", "locations"):
        if key not in entities or not isinstance(entities[key], list):
            entities[key] = []

    topic = normalize_topic(result.get("topic", "Other"))

    score = float(result.get("sentiment_score", 0.0))
    return {
        "sentiment_score": score,
        "sentiment_label": sentiment_label_for(score),
        "summary": result.get("summary", text[:100]),
        "entities": entities,
        "topic": topic,
    }


def neutral_result(text: str) -> dict:
    return {
        "sentiment_score": 0.0,
        "sentiment_label": "Neutral",
        "summary": text[:100],
        "entities": {"persons": [], "organizations": [], "locations": []},
        "topic": "Other",
    }
