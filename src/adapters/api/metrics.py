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

# Konu dengesi izleme (S2): hangi kaynak hangi konuda kaç haber getiriyor. Mevcut
# sayacın etiket kümesi değiştirilmedi (Grafana panelleri/testler bozulmasın).
articles_by_topic_total = Counter(
    "nexstream_articles_by_topic_total",
    "Saved articles by source and analysed topic",
    ["source", "topic"],
)

# Günlük kaynak tavanı dolduğu için o tur atlanan kaynaklar (S2) — tavanları
# ayarlamak için ölçüm: hangi kaynak sürekli tavana çarpıyor?
source_capped_total = Counter(
    "nexstream_source_capped_total",
    "Scrape runs skipped because the source hit its daily cap",
    ["source"],
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

# 7 Eki 2026 — RAG tam metin çekme (spec 2026-10-07-rag-tam-metin-design.md). `result`:
# hit (cache) / hit_failed (olumsuz cache isabeti) / fetched / failed (ağ, HTTP, ayrıştırma) / blocked (SSRF koruması ya da kaynak
# 401/403/429 ile reddetti) / too_short (çıkarılan metin kullanılamayacak kadar kısa).
# Host etiketi KASITLI yok: Hacker News gibi kaynaklar keyfi sitelere link verir (sınırsız
# kardinalite). Kaynak bazlı bakış için `failed`/`blocked` loglarındaki host'a (Loki) bak.
article_fetch_total = Counter(
    "nexstream_article_fetch_total",
    "Article full-text fetch attempts by result",
    ["result"],
)
# 7 Eki 2026 — RAG soru-cevap çağrılarının GERÇEK token tüketimi. `groq_tokens_total` yalnız worker
# analizini sayar; 120b TPD havuzundaki RAG payı (~50K/gün) hiç ölçülmüyordu. `kind`: prompt | completion.
rag_tokens_total = Counter(
    "nexstream_rag_tokens_total",
    "Groq tokens consumed by RAG question answering, from the API's own usage field",
    ["kind"],
)
article_fetch_seconds = Histogram(
    "nexstream_article_fetch_seconds",
    "Article full-text fetch duration in seconds",
    buckets=[0.25, 0.5, 1.0, 2.0, 3.0, 4.0, 6.0],
)
