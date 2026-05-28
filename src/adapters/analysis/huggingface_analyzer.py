import json
import logging
import time
from src.domain.ports.analysis_port import AnalysisPort, AnalysisError
from src.adapters.analysis.common import build_analysis_prompt, parse_analysis_json, neutral_result
from src.infrastructure.config.settings import settings

logger = logging.getLogger(__name__)


class HuggingFaceAnalyzer(AnalysisPort):
    """Groq yedeği — HuggingFace Inference API (ücretsiz tier, cloud-hosted, VPS'te çalışır).

    API key boşsa analyze_or_raise hemen AnalysisError fırlatır → FallbackAnalyzer atlar.
    """

    def __init__(self):
        self.api_key = settings.huggingface_api_key
        self.model = settings.huggingface_model
        self.api_url = f"https://api-inference.huggingface.co/models/{self.model}"

    def analyze_text(self, text: str) -> dict:
        try:
            return self.analyze_or_raise(text)
        except AnalysisError:
            return neutral_result(text)

    def analyze_or_raise(self, text: str) -> dict:
        import requests

        if not self.api_key:
            raise AnalysisError("HuggingFace API key tanımlı değil")

        headers = {"Authorization": f"Bearer {self.api_key}"}
        payload = {
            "inputs": build_analysis_prompt(text),
            "parameters": {"return_full_text": False, "max_new_tokens": 350, "temperature": 0.1},
        }

        for attempt in range(3):
            try:
                r = requests.post(self.api_url, headers=headers, json=payload, timeout=30)

                if r.status_code == 503:  # model soğuk başlatma — yüklenmesini bekle
                    wait = int(r.headers.get("retry-after", 5))
                    logger.warning("HuggingFace modeli yükleniyor, %ds bekleniyor...", wait)
                    time.sleep(wait)
                    continue

                r.raise_for_status()
                data = r.json()
                if isinstance(data, list) and data:
                    generated = data[0].get("generated_text", "")
                elif isinstance(data, dict):
                    generated = data.get("generated_text", "")
                else:
                    generated = ""
                return parse_analysis_json(generated, text)

            except json.JSONDecodeError:
                logger.warning("HuggingFace JSON parse hatası, deneme %d", attempt + 1)
                continue
            except Exception as e:
                logger.error("HuggingFace analiz hatası: %s", e)
                continue

        raise AnalysisError("HuggingFace: tüm denemeler başarısız")
