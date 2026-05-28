"""Analyzer'lar arası paylaşılan prompt + JSON ayrıştırma + nötr fallback.

Groq ve HuggingFace analyzer'ları aynı sözleşmeyi üretsin diye tek noktadan beslenir.
"""
import json
import re

VALID_TOPICS = {"Technology", "Sports", "Economy", "Politics", "Health", "Culture", "World", "Other"}


def build_analysis_prompt(text: str) -> str:
    return f"""Analyze the following news article. The article may be in English or Turkish — handle both.

Return ONLY a valid JSON object with these exact fields:
- sentiment_score: float between -1.0 and 1.0. Use the FULL range:
  * 0.7 to 1.0 = strongly positive (breakthrough, victory, celebration, major success)
  * 0.3 to 0.7 = mildly positive (improvement, progress, good outcome)
  * -0.2 to 0.2 = neutral (factual reporting, announcements, routine events)
  * -0.7 to -0.3 = mildly negative (concern, decline, setback, minor conflict)
  * -1.0 to -0.7 = strongly negative (disaster, death, crisis, severe harm)
- sentiment_label: "Positive" if score > 0.2, "Negative" if score < -0.2, otherwise "Neutral"
- summary: a 1-2 sentence summary of the article in the same language as the article
- entities: object with three arrays: "persons", "organizations", "locations" — extract named entities mentioned in the article. Each array may be empty.
- topic: exactly one of "Technology", "Sports", "Economy", "Politics", "Health", "Culture", "World", "Other"

Article:
{text[:1000]}

Respond with JSON only, no markdown, no explanation."""


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

    topic = result.get("topic", "Other")
    if topic not in VALID_TOPICS:
        topic = "Other"

    return {
        "sentiment_score": float(result.get("sentiment_score", 0.0)),
        "sentiment_label": result.get("sentiment_label", "Neutral"),
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
