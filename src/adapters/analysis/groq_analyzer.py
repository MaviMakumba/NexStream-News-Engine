"""Groq LLM adapter'ı — birincil analyzer (openai/gpt-oss-20b, v2.1.1'de değişti).

Tek prompt'ta sentiment + entities + topic + summary üretir (maliyet: 1 istek/haber).
Rate limit (429) yanıtında Retry-After header'ına uyar; 5 deneme sonrası
AnalysisError fırlatır (FallbackAnalyzer yedeğe geçsin diye).

v2.1.1 (18 Ağu 2026): `llama-3.1-8b-instant` Groq'un model listesinden tamamen
kaldırılmış (`model_not_found`, HTTP 404) — canlıda 17 Ağustos ~08:35 UTC'den
beri her haber sessizce nötr fallback'e düşüyordu (bkz. CLAUDE.md). Yerine
`openai/gpt-oss-20b` geçti: Groq'taki reasoning modelleri `content`'i
`reasoning`'den AYRI bir alanda döner (qwen3.6 gibi `<think>` etiketini content
içine gömen modellerin aksine), bu yüzden JSON parse'ı bozmuyor.
`reasoning_effort="low"` reasoning token bütçesini küçük tutuyor (~50 token);
`max_tokens` bu yüzden 350'den 600'e çıkarıldı (reasoning + JSON çıktısı için).
"""

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
        self.model = "openai/gpt-oss-20b"
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
            "max_tokens": 600,
            "temperature": 0.1,
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
