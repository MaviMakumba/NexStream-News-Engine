"""src/adapters/analysis/groq_question_answerer.py

RAG soru-cevap adapter'ı — kanıt paketinden TEK bir Groq çağrısıyla
yapılandırılmış bir sentez üretir (coverage/answer/used_sources).

GroqAnalyzer'daki rate-limit/retry HTTP deseninin (429 → Retry-After bekle,
5 deneme) birebir aynısı, ayrı bir prompt/parse mantığıyla (rag_common.py).

AnalysisPort'un aksine SESSİZ NÖTR FALLBACK YOK: tüm denemeler başarısız
olursa QuestionAnsweringError fırlatılır — bir soruya "kibarca uydurulmuş"
bir cevap vermek, açık bir hata vermekten daha kötü (bkz. spec "Amaç").

26 Ağu 2026'da canlıda bulunan bug: bu adapter ilk halinde GroqAnalyzer'ın
429 → Retry-After bekle deseni birebir kopyalanmıştı. GroqAnalyzer arka plan
worker'ında çalıştığı için bu doğru — ama bu adapter SENKRON bir kullanıcı
HTTP isteğinin (POST /api/v1/news/ask) içinde çalışıyor. Groq'un TPD rate
limit'i gözlemlenen Retry-After değerleri 3-7+ dakika (bkz. CLAUDE.md) —
bunu olduğu gibi `time.sleep()` ile beklemek kullanıcıyı dakikalarca
"Düşünüyor..." ekranında askıda bırakıyordu (canlıda doğrulandı). Bu yüzden
429'da BEKLEMEDEN hemen QuestionAnsweringError fırlatılır (fail-fast) —
kullanıcı birkaç saniye içinde net bir hata görüp isterse tekrar dener.

27 Ağu 2026'da canlıda bulunan İKİNCİ bug (roadmap #23'ün spike'ı buradan
çözüldü): bu adapter GroqAnalyzer (worker, 17 kaynak sürekli akış) ile AYNI
modeli (openai/gpt-oss-20b) kullanıyordu. Groq'un günlük token kotası (TPD)
MODEL BAŞINA ayrı bir havuz — resmi rate-limit dokümantasyonundaki tabloda
her model farklı bir TPD sayısıyla listeleniyor (aynı sayı olsa bile ayrı
sayaçlar — canlı ortamda iki modele art arda istek atılıp
`x-ratelimit-remaining-requests` header'ının HER model için BAĞIMSIZ
azaldığı doğrulandı, bkz. CLAUDE.md). Worker'ın sürekli tükettiği paylaşımlı
havuz RAG'a neredeyse hiç pay bırakmıyordu (canlıda aynı gün içinde 3 ayrı
429→503 gözlemlendi — "soru sor" kullanıcıya kalıcı bozuk gibi görünüyordu).
Çözüm: RAG'ı `openai/gpt-oss-120b`'ye taşımak — AYRI bir TPD havuzu açıyor,
aynı gpt-oss ailesinde kalındığı için `message.reasoning`/`content` ayrımı
korunuyor (qwen ailesi `<think>`'i content'e gömüp JSON parse'ı bozuyor,
bkz. CLAUDE.md "Groq modelleri" notu — o yüzden qwen'e GEÇİLMEDİ).
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
        # GroqAnalyzer'dan (openai/gpt-oss-20b) BİLİNÇLİ olarak farklı — aynı
        # modeli paylaşmak worker'ın sürekli tükettiği TPD havuzunu RAG'la
        # paylaştırıp aç bırakıyordu, bkz. modül docstring'i "27 Ağu 2026".
        self.model = "openai/gpt-oss-120b"
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

        for attempt in range(3):
            try:
                start = time.time()
                r = requests.post(self.api_url, headers=headers, json=payload, timeout=30)
                groq_latency_seconds.observe(time.time() - start)

                if r.status_code == 429:
                    groq_rate_limit_total.inc()
                    # Fail-fast: Retry-After'ı BEKLEME (bkz. modül docstring'i,
                    # 26 Ağu 2026 canlı bug'ı). Interaktif bir istek dakikalarca
                    # askıda kalamaz — kullanıcı hemen net bir hata görmeli.
                    logger.warning(
                        "Groq rate limit (soru-cevap) — interaktif istek beklemeden başarısız sayılıyor"
                    )
                    raise QuestionAnsweringError("Groq şu an kotasını doldurmuş, birazdan tekrar dene")

                r.raise_for_status()
                content = r.json()["choices"][0]["message"]["content"]
                return parse_rag_json(content)

            except json.JSONDecodeError:
                logger.warning("Groq soru-cevap JSON parse hatası, deneme %d", attempt + 1)
                continue
            except QuestionAnsweringError:
                raise
            except Exception as e:
                logger.error("Groq soru-cevap hatası: %s", e)
                if attempt < 1:
                    time.sleep(2)
                continue

        raise QuestionAnsweringError("Groq: tüm denemeler başarısız (soru-cevap)")
