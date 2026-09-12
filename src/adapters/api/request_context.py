"""İstek bağlamı: gerçek istemci IP'si + uçtan uca request_id (13 Eylül 2026).

Güven sınırı — neden `X-Real-IP`/`X-Request-ID` header'larına güveniyoruz:
prod'da app iç ağda, sadece nginx ulaşıyor (SG: origin'e yalnızca Cloudflare);
nginx her iki header'ı da KENDİ değerleriyle yazar (`proxy_set_header X-Real-IP
$remote_addr`, `X-Request-ID $request_id`), istemcinin gönderdiğini ezer;
`$remote_addr` da Cloudflare `set_real_ip_from` düzeltmesinden geçmiştir.
Header yoksa (dev, doğrudan 8000 portu) bağlantı adresine / kendi ürettiğimiz
id'ye düşeriz.

Bulgu: uvicorn `--proxy-headers`/`--forwarded-allow-ips` ile başlatılmadığı
için `request.client.host` prod'da NGINX'in iç IP'siydi — slowapi
`get_remote_address` ile tüm ziyaretçileri tek kovada sayıyordu. `client_ip`
artık limiter'ın da anahtarı (limiter.py).

`request_id` bir ContextVar'da tutulur: JSON logger her satıra ekler, güvenlik
günlüğü (`security_audit.py`) satıra yazar, yanıt header'ında geri döner.
"""

import contextvars
import re
import uuid
from typing import Optional

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

REQUEST_ID_HEADER = "X-Request-ID"
_REQUEST_ID_RE = re.compile(r"[^A-Za-z0-9-]")
_REQUEST_ID_MAX_LEN = 64

_request_id_var: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar("request_id", default=None)


def client_ip(request: Request) -> str:
    """nginx'in yazdığı X-Real-IP, yoksa bağlantı adresi (dev/test)."""
    real_ip = request.headers.get("x-real-ip")
    if real_ip:
        return real_ip.strip()
    return request.client.host if request.client else "unknown"


def current_request_id() -> Optional[str]:
    return _request_id_var.get()


def bind_request_id(request_id: Optional[str], token: Optional[contextvars.Token] = None):
    """ContextVar'ı ayarlar (token verilirse geri alır). Middleware ve testler kullanır."""
    if token is not None:
        _request_id_var.reset(token)
        return None
    return _request_id_var.set(request_id)


def _sanitize(raw: Optional[str]) -> Optional[str]:
    if not raw:
        return None
    cleaned = _REQUEST_ID_RE.sub("", raw)[:_REQUEST_ID_MAX_LEN]
    return cleaned or None


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = _sanitize(request.headers.get(REQUEST_ID_HEADER)) or uuid.uuid4().hex
        token = bind_request_id(request_id)
        try:
            response = await call_next(request)
        finally:
            bind_request_id(None, token)
        response.headers[REQUEST_ID_HEADER] = request_id
        return response
