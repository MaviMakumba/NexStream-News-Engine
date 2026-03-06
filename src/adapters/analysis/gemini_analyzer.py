import os
from google import genai
from src.domain.ports.analysis_port import AnalysisPort

class GeminiAnalyzer(AnalysisPort):

    def __init__(self):
        self.client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
        self.model = "gemini-2.5-flash"

    def analyze_text(self, text: str) -> dict:
        if not text:
            return {
                "sentiment_score": 0.0,
                "sentiment_label": "Neutral",
                "summary": "No Content"
            }

        prompt = f"""Analyze the following news text and respond ONLY with a JSON object.
No explanation, no markdown, just raw JSON.

Text: {text}

Response format:
{{
  "sentiment_label": "Positive" or "Negative" or "Neutral",
  "sentiment_score": a float between -1.0 and 1.0,
  "summary": "one sentence summary in English"
}}"""

        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=prompt
            )
            raw = response.text.strip()

            # Markdown code block varsa temizle
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
                raw = raw.strip()

            import json
            result = json.loads(raw)

            return {
                "sentiment_score": float(result.get("sentiment_score", 0.0)),
                "sentiment_label": result.get("sentiment_label", "Neutral"),
                "summary": result.get("summary", text[:100]),
            }

        except Exception as e:
            print(f"❌ Gemini analiz hatası: {e}")
            return {
                "sentiment_score": 0.0,
                "sentiment_label": "Neutral",
                "summary": text[:100]
            }