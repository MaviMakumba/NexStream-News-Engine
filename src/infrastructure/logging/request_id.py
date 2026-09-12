"""İstek kimliği (request_id) ContextVar'ı — framework bağımsız (13 Eylül 2026).

`logger.py` her JSON satırına request_id ekler; bu değeri HTTP katmanı
(`adapters/api/request_context.py`) set eder. ContextVar'ın burada, altyapı
katmanında yaşamasının sebebi bağımlılık yönü: infrastructure hiçbir adapter'ı
import edemez. Aksi (logger → adapters/api → fastapi) 13 Eyl 2026'da scheduler'ı
(fastapi'siz light image) crash-loop'a soktu. Worker/scheduler gibi HTTP'siz
süreçlerde değer hep None kalır, log satırında alan hiç yazılmaz.
"""

import contextvars
from typing import Optional

_request_id_var: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar("request_id", default=None)


def current_request_id() -> Optional[str]:
    return _request_id_var.get()


def bind_request_id(request_id: Optional[str], token: Optional[contextvars.Token] = None):
    """ContextVar'ı ayarlar; `token` verilirse önceki değere geri alır."""
    if token is not None:
        _request_id_var.reset(token)
        return None
    return _request_id_var.set(request_id)
