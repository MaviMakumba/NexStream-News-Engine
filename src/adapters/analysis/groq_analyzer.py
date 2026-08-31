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

31 Ağu 2026: `openai/gpt-oss-20b`'nin RPM=30 limiti VAR ama asıl darboğaz
TPM=8000 (token/dakika) — çağıran taraftaki sabit 2sn throttle SADECE RPM'i
hedefliyordu, TPM'i hiç hesaba katmıyordu (2sn ile dakikada 30 istek deneniyor,
istek başına ~700-1000 token ile bu ~25-30K token/dk demek, TPM tavanının
~3 katı). Sonuç: bir kaynağın birikmiş haberlerinde ilk birkaç istekte hemen
429'a çarpılıyor, Groq dakikalarca bekleme dayatıyor, pipeline saatlerce geri
düşüyor. Sabit bir "daha uzun bekle" tahmini yerine Groq'un HER yanıtta
döndürdüğü `x-ratelimit-remaining-tokens`/`x-ratelimit-reset-tokens`
header'ları okunuyor — kalan bütçe güvenlik payının altına düşünce, 429
gelmesini BEKLEMEDEN, Groq'un kendi bildirdiği süre kadar proaktif bekleniyor
(bkz. `_throttle_for_remaining_budget`). Kendi kendini kalibre eder, prompt
uzunluğu/model davranışı değişse de sabit bir sayıya bağlı kalmaz.
"""

import json
import logging
import re
import time
from src.domain.ports.analysis_port import AnalysisPort, AnalysisError
from src.adapters.analysis.common import build_analysis_prompt, parse_analysis_json, neutral_result
from src.infrastructure.config.settings import settings
from src.adapters.api.metrics import groq_latency_seconds, groq_rate_limit_total

logger = logging.getLogger(__name__)

_DURATION_RE = re.compile(r"(?:(\d+)m)?([\d.]+)s")


class GroqAnalyzer(AnalysisPort):
    # Bu eşiğin altına düşen kalan TPM bütçesi, bir sonraki isteğin (prompt +
    # completion, gözlemlenen ortalama ~700-1000 token) 429'a çarpma riskini
    # taşıdığı anlamına gelir — güvenlik payı olarak biraz yüksek tutuldu.
    _TOKEN_SAFETY_MARGIN = 1000

    def __init__(self):
        self.api_key = settings.groq_api_key
        self.model = "openai/gpt-oss-20b"
        self.api_url = "https://api.groq.com/openai/v1/chat/completions"

    @staticmethod
    def _parse_duration(value: str) -> float:
        """Groq'un 'x-ratelimit-reset-*' header'larındaki '2m59.56s' / '7.66s'
        formatını saniyeye çevirir. Tanınmayan/boş girdide 0.0 döner (çökmez)."""
        if not value:
            return 0.0
        match = _DURATION_RE.match(value.strip())
        if not match:
            return 0.0
        minutes = float(match.group(1) or 0)
        seconds = float(match.group(2) or 0)
        return minutes * 60 + seconds

    def _throttle_for_remaining_budget(self, headers) -> None:
        """TPM tavanına yaklaşıldıysa, 429 gelmesini BEKLEMEDEN Groq'un kendi
        bildirdiği süre kadar proaktif bekler. Header eksik/parse edilemezse
        VEYA `headers` gerçek bir dict-benzeri değilse (ör. test mock'u —
        `MagicMock().get(...)` string değil başka bir MagicMock döndürür,
        `int()`/`.strip()` sessizce "başarılı" görünüp yanlış değer üretebilir)
        sessizce atlanır — mevcut reaktif 429 akışı zaten bir güvenlik ağı."""
        remaining_raw = headers.get("x-ratelimit-remaining-tokens")
        if not isinstance(remaining_raw, str):
            return
        try:
            remaining = int(remaining_raw)
        except ValueError:
            return
        if remaining >= self._TOKEN_SAFETY_MARGIN:
            return
        reset_raw = headers.get("x-ratelimit-reset-tokens")
        wait = self._parse_duration(reset_raw) if isinstance(reset_raw, str) else 0.0
        if wait > 0:
            logger.info(
                "Groq TPM tavanına yakın (%d token kaldı), %.2fs proaktif bekleniyor...",
                remaining, wait,
            )
            time.sleep(wait)

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
                self._throttle_for_remaining_budget(r.headers)
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
