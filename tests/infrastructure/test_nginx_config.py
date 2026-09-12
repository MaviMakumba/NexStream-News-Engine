"""Prod nginx yapılandırması regresyon testleri.

12 Eylül 2026 güvenlik turu: `/api/metrics` (Prometheus metrikleri — endpoint
listesi, istek sayıları, Groq token sayacı) genel `/api/` proxy bloğu üzerinden
herkese açıktı; canlıda bir "güvenlik araştırmacısı" okudu. Prometheus metrikleri
Docker iç ağından (`app:8000/metrics`) topluyor, nginx üzerinden hiç geçmiyor —
dışarıya kapatmak hiçbir şeyi bozmaz.
"""

import re

_NGINX_CONF = "infra/nginx/nginx.conf"


def _conf() -> str:
    with open(_NGINX_CONF, "r", encoding="utf-8") as f:
        return f.read()


def test_prod_nginx_blocks_public_metrics():
    conf = _conf()
    block = re.search(r"location\s*=\s*/api/metrics\s*\{(?P<body>[^}]*)\}", conf)
    assert block, "nginx.conf'ta `location = /api/metrics { ... }` bloğu yok"
    assert re.search(r"return\s+404", block.group("body")), "metrics bloğu 404 dönmüyor"
