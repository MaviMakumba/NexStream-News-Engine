"""Prometheus custom metrikleri — /metrics endpoint'inde dışa verilir.

İsimlendirme: nexstream_<konu>_<birim>. Yeni metrik eklerken burada tanımla,
kullanan modüle import et (tek doğruluk noktası).
"""

from prometheus_client import Counter, Histogram

articles_processed_total = Counter(
    "nexstream_articles_processed_total",
    "Total articles processed by the pipeline",
    ["source", "status"],
)

groq_latency_seconds = Histogram(
    "nexstream_groq_latency_seconds",
    "Groq API call latency in seconds",
    buckets=[0.5, 1.0, 2.0, 3.0, 5.0, 10.0, 30.0],
)

groq_rate_limit_total = Counter(
    "nexstream_groq_rate_limit_total",
    "Total Groq API rate limit hits",
)

search_latency_seconds = Histogram(
    "nexstream_search_latency_seconds",
    "Search endpoint latency in seconds",
    buckets=[0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0],
)

# v2.1.1 (18 Ağu 2026) — Groq'un modeli tamamen kaldırması bir gün boyunca fark
# edilmedi çünkü FallbackAnalyzer'ın nötr fallback'i (bilinçli tasarım: servis
# hot-path'i çökmesin) hiçbir sinyal bırakmıyordu. Bu sayaç artık Grafana
# alerting'in "analiz kalitesi sessizce bozuldu mu" sorusuna cevap vermesini
# sağlıyor — bkz. infra/grafana/provisioning/alerting/.
analysis_fallback_total = Counter(
    "nexstream_analysis_fallback_total",
    "Total times ALL analyzers failed and a neutral default was returned",
)
