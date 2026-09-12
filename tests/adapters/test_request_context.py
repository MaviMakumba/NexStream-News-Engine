"""İstek bağlamı: gerçek istemci IP'si + uçtan uca request_id (13 Eylül 2026).

Güven sınırı: prod'da app iç ağda, sadece nginx ulaşıyor; nginx `X-Real-IP`'yi
kendi `$remote_addr`'ından (Cloudflare düzeltmesi geçmiş) yazıp istemcinin
gönderdiğini EZİYOR, `X-Request-ID`'yi de kendi `$request_id`'sinden basıyor.
Bu yüzden app bu iki header'a güvenebilir; header yoksa (dev, doğrudan 8000)
bağlantı adresine / kendi ürettiği id'ye düşer.

Bulgu (13 Eyl): uvicorn `--proxy-headers`/`--forwarded-allow-ips` ile
başlatılmıyor → `request.client.host` prod'da NGINX'in iç IP'si; slowapi
`get_remote_address` ile TÜM ziyaretçileri tek kovada sayıyordu. `client_ip`
artık limiter'ın da anahtarı.
"""

import re

from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from src.adapters.api.request_context import client_ip, current_request_id, RequestContextMiddleware
from src.adapters.api.limiter import limiter


def _app():
    app = FastAPI()
    app.add_middleware(RequestContextMiddleware)

    @app.get("/who")
    def who(request: Request):
        return {"ip": client_ip(request), "rid": current_request_id()}

    return app


def test_client_ip_prefers_x_real_ip_set_by_nginx():
    c = TestClient(_app())
    r = c.get("/who", headers={"X-Real-IP": "78.186.147.254", "X-Forwarded-For": "1.2.3.4, 5.6.7.8"})
    assert r.json()["ip"] == "78.186.147.254"


def test_client_ip_falls_back_to_connection_address_without_header():
    c = TestClient(_app())
    assert c.get("/who").json()["ip"] == "testclient"


def test_request_id_taken_from_nginx_header_and_echoed_in_response():
    c = TestClient(_app())
    r = c.get("/who", headers={"X-Request-ID": "abc123def456"})
    assert r.json()["rid"] == "abc123def456"
    assert r.headers["X-Request-ID"] == "abc123def456"


def test_request_id_generated_when_header_missing():
    c = TestClient(_app())
    r = c.get("/who")
    rid = r.json()["rid"]
    assert re.fullmatch(r"[0-9a-f]{32}", rid)
    assert r.headers["X-Request-ID"] == rid


def test_request_id_header_is_sanitized_and_length_capped():
    """nginx ezmiyorsa bile (dev) log enjeksiyonu olmasın: sadece [A-Za-z0-9-], en fazla 64."""
    c = TestClient(_app())
    r = c.get("/who", headers={"X-Request-ID": "x" * 100 + "\n{evil}"})
    rid = r.json()["rid"]
    assert re.fullmatch(r"[A-Za-z0-9-]{1,64}", rid)


def test_limiter_keys_on_client_ip():
    assert limiter._key_func is client_ip
