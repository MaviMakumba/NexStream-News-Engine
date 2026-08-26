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
