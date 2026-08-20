"""src/adapters/analysis/groq_query_expander.py

Groq tabanlı sorgu genişletme adapter'ı — arama sorgusuyla ilişkili ek
terimler üretir ("istanbul" → ilçeleri, "futbol" → büyük takımlar).

Spike'ta (20 Ağu 2026, bkz. spec) doğrulandı: "istanbul" için gerçek ilçe
isimleri üretti (Fatih, Beyoğlu, Kadıköy...), 0.8sn. Her hata yolu
(429/timeout/bozuk JSON/model kaldırılmış) boş liste ile sonuçlanır —
arama ASLA bu adaptör yüzünden bozulmaz (projenin "Exception'ları yut,
logla, fallback dön" kuralı).
"""

import json
import logging
import re
from typing import List

import requests

from src.domain.ports.query_expansion_port import QueryExpansionPort
from src.infrastructure.config.settings import settings

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
        self.model = "openai/gpt-oss-20b"
        self.api_url = "https://api.groq.com/openai/v1/chat/completions"

    def expand(self, query: str) -> List[str]:
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
            r = requests.post(self.api_url, headers=headers, json=payload, timeout=10)
            if r.status_code != 200:
                logger.warning("Sorgu genişletme başarısız (status=%d): %s", r.status_code, r.text[:200])
                return []
            content = r.json()["choices"][0]["message"]["content"]
            match = re.search(r"\{.*\}", content, re.DOTALL)
            parsed = json.loads(match.group(0)) if match else json.loads(content)
            terms = parsed.get("terms", [])
            clean = [t.strip() for t in terms if isinstance(t, str) and t.strip()]
            return clean[:_MAX_TERMS]
        except Exception as e:
            logger.warning("Sorgu genişletme hatası: %s", e)
            return []
