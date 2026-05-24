import json
import logging
import re
import time
from src.domain.ports.analysis_port import AnalysisPort
from src.infrastructure.config.settings import settings

logger = logging.getLogger(__name__)


class GroqAnalyzer(AnalysisPort):
    def __init__(self):
        self.api_key = settings.groq_api_key
        self.model = "llama-3.1-8b-instant"
        self.api_url = "https://api.groq.com/openai/v1/chat/completions"

    def analyze_text(self, text: str) -> dict:
        import requests

        prompt = f"""Analyze the following news article. The article may be in English or Turkish — handle both.

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

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 350,
            "temperature": 0.1,
        }

        for attempt in range(5):
            try:
                r = requests.post(self.api_url, headers=headers, json=payload, timeout=30)

                if r.status_code == 429:
                    wait = int(r.headers.get("retry-after", 5))
                    logger.warning("Groq rate limit, %ds bekleniyor...", wait)
                    time.sleep(wait)
                    continue

                r.raise_for_status()
                content = r.json()["choices"][0]["message"]["content"]
                content = re.sub(r"```json|```", "", content).strip()
                result = json.loads(content)

                entities = result.get("entities", {})
                if not isinstance(entities, dict):
                    entities = {}
                for key in ("persons", "organizations", "locations"):
                    if key not in entities or not isinstance(entities[key], list):
                        entities[key] = []

                valid_topics = {"Technology", "Sports", "Economy", "Politics", "Health", "Culture", "World", "Other"}
                topic = result.get("topic", "Other")
                if topic not in valid_topics:
                    topic = "Other"

                return {
                    "sentiment_score": float(result.get("sentiment_score", 0.0)),
                    "sentiment_label": result.get("sentiment_label", "Neutral"),
                    "summary": result.get("summary", text[:100]),
                    "entities": entities,
                    "topic": topic,
                }

            except json.JSONDecodeError:
                logger.warning("Groq JSON parse hatası, deneme %d", attempt + 1)
                continue
            except Exception as e:
                logger.error("Groq analiz hatası: %s", e)
                if attempt < 2:
                    time.sleep(5)
                continue

        return {
            "sentiment_score": 0.0,
            "sentiment_label": "Neutral",
            "summary": text[:100],
            "entities": {"persons": [], "organizations": [], "locations": []},
            "topic": "Other",
        }
