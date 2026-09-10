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

import threading
from src.domain.ports.analysis_port import AnalysisPort
from src.adapters.analysis.groq_analyzer import GroqAnalyzer

_budget_lock = threading.Lock()
_remaining_tokens: dict[str, int] = {}  # model adı -> son bilinen kalan TPM


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
    def __init__(self, models: list[str]):
        self._analyzers: dict[str, GroqAnalyzer] = {m: GroqAnalyzer(model=m) for m in models}

    def analyze_text(self, text: str) -> dict:
        model = pick_least_loaded(list(self._analyzers))
        return self._analyzers[model].analyze_text(text)
