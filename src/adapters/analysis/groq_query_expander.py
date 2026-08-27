"""src/adapters/analysis/groq_query_expander.py

Groq tabanlı sorgu genişletme adapter'ı — arama sorgusuyla ilişkili ek
terimler üretir ("istanbul" → ilçeleri, "futbol" → büyük takımlar).

Spike'ta (20 Ağu 2026, bkz. spec) doğrulandı: "istanbul" için gerçek ilçe
isimleri üretti (Fatih, Beyoğlu, Kadıköy...), 0.8sn. Her hata yolu
(429/timeout/bozuk JSON/model kaldırılmış) boş liste ile sonuçlanır —
arama ASLA bu adaptör yüzünden bozulmaz (projenin "Exception'ları yut,
logla, fallback dön" kuralı).

27 Ağu 2026'da canlı QA diagnostiğinde bulundu: GroqAnalyzer (worker, 17
kaynak sürekli akış) ile AYNI modeli (openai/gpt-oss-20b) paylaşıyordu —
GroqQuestionAnswerer için doğrulanan model-başına-ayrı-TPD-havuzu bilgisiyle
(roadmap #23) `openai/gpt-oss-120b`'ye taşındı. Fail-open olduğu için
paylaşımlı kota dolunca arama ASLA bozulmuyordu ama genişletme özelliği
sessizce hep boş dönüyordu (canlıda art arda 6 sorguda 6'sı da 429).
"""

import json
import logging
import re
import time
from typing import List

import requests

from src.domain.ports.query_expansion_port import QueryExpansionPort
from src.infrastructure.config.settings import settings
from src.adapters.api.metrics import (
    groq_latency_seconds,
    groq_rate_limit_total,
    query_expansion_total,
)

logger = logging.getLogger(__name__)

_PROMPT_TEMPLATE = """Sen bir Türkçe haber arama motorunun sorgu genişletme asistanısın.
Kullanıcı "{query}" diye arattı. Bu sorguyla ANLAMCA/İLİŞKİSEL olarak yakın,
haber arama sonuçlarını zenginleştirecek 3-6 ek terim üret.

Kurallar:
- Sorgu bir şehir/il ise: bilinen büyük ilçelerini/semtlerini ekle.
- Sorgu bir spor dalıysa: o daldaki büyük/bilinen takım isimlerini ekle.
- Sorgu bir ekonomik/siyasi kavramsa: ilgili kurum/kişi/parti isimlerini ekle.
- Sorgunun kendisini tekrar ETME, SADECE yeni terimler ver.
- Emin değilsen az terim üret, uydurma/yanlış bilgi verme.

SADECE şu JSON formatında yanıt ver, başka hiçbir metin ekleme:
{{"terms": ["terim1", "terim2", ...]}}

Sorgu: {query}"""

_MAX_TERMS = 6


class GroqQueryExpander(QueryExpansionPort):
    def __init__(self):
        self.api_key = settings.groq_api_key
        # GroqAnalyzer'dan (openai/gpt-oss-20b) BİLİNÇLİ olarak farklı — bkz.
        # modül docstring'i "27 Ağu 2026" (GroqQuestionAnswerer'daki aynı
        # düzeltmeyle tutarlı, ayrı bir TPD havuzu açar).
        self.model = "openai/gpt-oss-120b"
        self.api_url = "https://api.groq.com/openai/v1/chat/completions"

    def expand(self, query: str) -> List[str]:
        # Boş sorgu ETİKETLENMEZ: Groq'a hiç gidilmiyor, bu bir "genişletme
        # denemesi" değil. "empty" saymak, metriğin asıl anlamını ("Groq yanıt
        # verdi ama ilişkili terim bulamadı") çağıran taraftaki no-op'larla
        # sulandırırdı.
        if not query or not query.strip():
            return []
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": _PROMPT_TEMPLATE.format(query=query)}],
            "temperature": 0.3,
            "max_tokens": 300,
            "reasoning_effort": "low",
        }
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        try:
            start = time.time()
            r = requests.post(self.api_url, headers=headers, json=payload, timeout=10)
            groq_latency_seconds.observe(time.time() - start)

            if r.status_code == 429:
                groq_rate_limit_total.inc()

            if r.status_code != 200:
                logger.warning("Sorgu genişletme başarısız (status=%d): %s", r.status_code, r.text[:200])
                query_expansion_total.labels(result="error").inc()
                return []

            content = r.json()["choices"][0]["message"]["content"]
            match = re.search(r"\{.*\}", content, re.DOTALL)
            parsed = json.loads(match.group(0)) if match else json.loads(content)
            terms = parsed.get("terms", [])
            if not isinstance(terms, list):
                terms = []
            clean = [t.strip() for t in terms if isinstance(t, str) and t.strip()][:_MAX_TERMS]
            query_expansion_total.labels(result="expanded" if clean else "empty").inc()
            return clean
        except Exception as e:
            logger.warning("Sorgu genişletme hatası: %s", e)
            query_expansion_total.labels(result="error").inc()
            return []
