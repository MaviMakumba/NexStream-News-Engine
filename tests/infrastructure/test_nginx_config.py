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


def test_acme_challenge_served_on_https_too():
    """13 Eyl 2026: Cloudflare 'Always Use HTTPS' HTTP-01 isteğini 443'e
    yönlendirebilir — 443 bloğunda acme location yoksa istek frontend'e düşüp
    404 verir ve sertifika yenilemesi sessizce kırılır. Her iki server bloğunda
    da aynı webroot location olmalı."""
    conf = _conf()
    https_block = conf.split("listen 443 ssl default_server;", 1)[1]
    assert re.search(r"location\s+/\.well-known/acme-challenge/\s*\{[^}]*root\s+/var/www/certbot", https_block)


def test_grafana_proxy_keeps_subpath_prefix():
    """13 Eyl 2026: `proxy_pass $grafana_upstream/;` (sondaki `/`) /grafana/ önekini
    SİLİP Grafana'ya `/` gönderiyordu; Grafana serve_from_sub_path=true ile
    `/grafana/`'ye geri yönlendirince sonsuz 301 döngüsü oluştu (root URL
    localhost'tan gerçek domain'e çevrilince ortaya çıktı). Grafana'nın kendi
    dokümanındaki nginx örneği önekli geçirir: proxy_pass'te URI parçası OLMAMALI."""
    conf = _conf()
    block = re.search(r"location\s+/grafana/\s*\{(?P<body>[^}]*)\}", conf)
    assert block
    assert re.search(r"proxy_pass\s+\$grafana_upstream\s*;", block.group("body")), block.group("body")
