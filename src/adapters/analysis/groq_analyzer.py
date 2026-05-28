import json
import logging
import time
from src.domain.ports.analysis_port import AnalysisPort, AnalysisError
from src.adapters.analysis.common import build_analysis_prompt, parse_analysis_json, neutral_result
from src.infrastructure.config.settings import settings
from src.adapters.api.metrics import groq_latency_seconds, groq_rate_limit_total

logger = logging.getLogger(__name__)


class GroqAnalyzer(AnalysisPort):
    def __init__(self):
        self.api_key = settings.groq_api_key
        self.model = "llama-3.1-8b-instant"
        self.api_url = "https://api.groq.com/openai/v1/chat/completions"

    def analyze_text(self, text: str) -> dict:
        try:
            return self.analyze_or_raise(text)
        except AnalysisError:
            return neutral_result(text)

    def analyze_or_raise(self, text: str) -> dict:
        import requests

        prompt = build_analysis_prompt(text)
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
                start = time.time()
                r = requests.post(self.api_url, headers=headers, json=payload, timeout=30)
                groq_latency_seconds.observe(time.time() - start)

                if r.status_code == 429:
                    groq_rate_limit_total.inc()
                    wait = int(r.headers.get("retry-after", 5))
                    logger.warning("Groq rate limit, %ds bekleniyor...", wait)
                    time.sleep(wait)
                    continue

                r.raise_for_status()
                content = r.json()["choices"][0]["message"]["content"]
                return parse_analysis_json(content, text)

            except json.JSONDecodeError:
                logger.warning("Groq JSON parse hatası, deneme %d", attempt + 1)
                continue
            except Exception as e:
                logger.error("Groq analiz hatası: %s", e)
                if attempt < 2:
                    time.sleep(5)
                continue

        raise AnalysisError("Groq: tüm denemeler başarısız")
