"""Groq ana analiz pipeline'ı için havuz bölme — TPM darboğazını iki bağımsız
model kovasına dağıtır (spec: docs/superpowers/specs/2026-09-10-groq-darbogazi-design.md).

10 Eylül 2026'da canlıda ölçüldü: openai/gpt-oss-20b TEK BAŞINA 17 kaynağın
trafiğini karşılayamıyordu (TPM=8000, tek bir istek 184s'lik proaktif
beklemeye takıldı). qwen/qwen3.8-27b AYRI bir 8000 TPM kovasına sahip
(gerçek Groq header'larıyla doğrulandı) ve gpt-oss ailesi gibi content/
reasoning ayrımı temiz (qwen3.6-27b'nin aksine - o <think> etiketini content
içine gömüyor, KULLANILMADI).

Kaynak->model statik ataması YOK: her çağrıda hangi modelin bütçesi daha
rahatsa oraya gidilir (GroqAnalyzer'ın zaten okuduğu x-ratelimit-remaining-
tokens header'ının doğal bir uzantısı). Yeni bir kaynak eklenince hiçbir ek
karar/config gerekmez.
"""

import logging
import threading
import time
from src.domain.ports.analysis_port import AnalysisPort, AnalysisError
from src.adapters.analysis.common import neutral_result
from src.adapters.analysis.groq_analyzer import GroqAnalyzer, GroqRateLimited

logger = logging.getLogger(__name__)

_budget_lock = threading.Lock()
_remaining_tokens: dict[str, int] = {}  # model adı -> son bilinen kalan TPM
_cooldown_until: dict[str, float] = {}  # model adı -> 429 sonrası tekrar denenebileceği an (monotonic)


def record_remaining(model: str, remaining: int) -> None:
    """GroqAnalyzer her Groq yanıtından sonra bu modelin kalan TPM bütçesini
    buraya yazar (thread-safe - worker çağrıları run_in_executor thread
    pool'unda çalışıyor)."""
    with _budget_lock:
        _remaining_tokens[model] = remaining


def pick_least_loaded(models: list[str]) -> str:
    """Hiç çağrılmamış model tam bütçeli (sonsuz) sayılır - önce o denenir."""
    with _budget_lock:
        return max(models, key=lambda m: _remaining_tokens.get(m, float("inf")))


class PooledGroqAnalyzer(AnalysisPort):
    """Her çağrıda soğumada OLMAYAN modeller arasından en rahatını seçer.

    28 Eyl 2026: seçim sadece TPM'e bakıyordu, bağlayıcı limit ise günlük
    token kovası (TPD) çıktı — 20b 429 alınca aynı modelde ~200 sn uyunuyor,
    qwen'in kotası boş kalıyordu (24 saatte 248K'ya 1.3K token). Artık 429
    alan model Retry-After kadar soğumaya alınır ve istek hemen diğer modele
    gider; sadece HEPSİ soğumadaysa en erken açılacak olan beklenir.
    """

    # Tüm modellerin sürekli 429 döndüğü patolojik durumda sonsuz döngüye
    # girmemek için üst sınır (model başına birkaç tur).
    _MAX_ATTEMPTS_PER_MODEL = 3

    def __init__(self, models: list[str], clock=time.monotonic, sleep=time.sleep):
        self._analyzers: dict[str, GroqAnalyzer] = {
            m: GroqAnalyzer(model=m, wait_on_rate_limit=False) for m in models
        }
        self._clock = clock
        self._sleep = sleep

    def analyze_text(self, text: str) -> dict:
        try:
            return self.analyze_or_raise(text)
        except AnalysisError:
            return neutral_result(text)

    def analyze_or_raise(self, text: str) -> dict:
        models = list(self._analyzers)
        for _ in range(len(models) * self._MAX_ATTEMPTS_PER_MODEL):
            now = self._clock()
            with _budget_lock:
                available = [m for m in models if _cooldown_until.get(m, 0) <= now]
                earliest = min((_cooldown_until.get(m, 0) for m in models), default=now)
            if not available:
                wait = max(0.0, earliest - now)
                logger.warning("Havuzdaki tüm Groq modelleri soğumada, %.0fs bekleniyor...", wait)
                self._sleep(wait)
                continue
            model = pick_least_loaded(available)
            try:
                return self._analyzers[model].analyze_or_raise(text)
            except GroqRateLimited as e:
                with _budget_lock:
                    _cooldown_until[model] = self._clock() + e.retry_after
        raise AnalysisError("Groq havuzu: tüm modeller rate limit'te, deneme sınırı aşıldı")
