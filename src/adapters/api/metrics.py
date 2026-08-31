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

# v2.3 (20 Ağu 2026) — arama sorgu genişletme de fail-open bir Groq yolu:
# hata durumunda sessizce boş liste dönüyor, arama çalışmaya devam ediyor, hiçbir
# sinyal kalmıyor. `analysis_fallback_total` ile AYNI kör noktayı (yukarıdaki
# "Groq sessizce bozuldu" deseni) bu yeni yol için de kapatır. `result` etiketi:
# hit (cache — Groq'a hiç gidilmedi) / expanded (≥1 terim) / empty (başarılı ama
# 0 terim, geçerli bir sonuç) / error (istek veya parse başarısız).
query_expansion_total = Counter(
    "nexstream_query_expansion_total",
    "Total query expansion attempts by result",
    ["result"],
)

# 31 Ağu 2026 (roadmap #25, TPD maliyeti düşürme) — o zamana kadar Groq'un
# GERÇEK token tüketimi hiç yakalanmıyordu, TPD kısıtı sadece rate-limit
# header'larından/canlı gözlemden TAHMİN ediliyordu (bkz. CLAUDE.md BİLİNEN
# NOTLAR). Groq'un OpenAI-uyumlu yanıtındaki `usage` alanı artık burada
# sayılıyor — Grafana'da gerçek prompt/completion oranı ve model başına
# günlük toplam görülebilir, bir sonraki maliyet-azaltma turu tahmine değil
# ölçüme dayanabilir. `kind`: "prompt" | "completion".
groq_tokens_total = Counter(
    "nexstream_groq_tokens_total",
    "Total Groq tokens consumed, from the API's own usage field",
    ["model", "kind"],
)
