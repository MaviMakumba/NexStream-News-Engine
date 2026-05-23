import os
import json
import re
import time
from src.domain.ports.analysis_port import AnalysisPort

class GroqAnalyzer(AnalysisPort):
    def __init__(self):
        self.api_key = os.getenv("GROQ_API_KEY")
        self.model = "llama-3.1-8b-instant"
        self.api_url = "https://api.groq.com/openai/v1/chat/completions"

    def analyze_text(self, text: str) -> dict:
        import requests

        prompt = f"""Analyze the sentiment of the following news article. The article may be in English or Turkish — handle both.

Return ONLY a valid JSON object with these exact fields:
- sentiment_score: float between -1.0 (very negative) and 1.0 (very positive)
- sentiment_label: exactly one of "Positive", "Negative", or "Neutral"
- summary: a 1-2 sentence English summary of the article

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
            "max_tokens": 200,
            "temperature": 0.1,
        }

        for attempt in range(5):
            try:
                r = requests.post(self.api_url, headers=headers, json=payload, timeout=30)

                if r.status_code == 429:
                    wait = int(r.headers.get("retry-after", 5))
                    print(f"⏳ Rate limit, {wait}s bekleniyor...")
                    time.sleep(wait)
                    continue

                r.raise_for_status()
                content = r.json()["choices"][0]["message"]["content"]

                # Strip markdown fences if present
                content = re.sub(r"```json|```", "", content).strip()
                result = json.loads(content)

                return {
                    "sentiment_score": float(result.get("sentiment_score", 0.0)),
                    "sentiment_label": result.get("sentiment_label", "Neutral"),
                    "summary": result.get("summary", text[:100]),
                }

            except json.JSONDecodeError:
                print(f"⚠️ JSON parse hatası, deneme {attempt + 1}")
                continue
            except Exception as e:
                print(f"❌ Groq analiz hatası: {e}")
                if attempt < 2:
                    time.sleep(5)
                continue

        return {"sentiment_score": 0.0, "sentiment_label": "Neutral", "summary": text[:100]}