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
