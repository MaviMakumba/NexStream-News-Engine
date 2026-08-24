"""Hata takibi (Sentry) — opsiyonel, fail-open kurulum (v2.4).

Diğer opsiyonel entegrasyonlarla (Redis, HuggingFace, Resend) aynı desen:
`SENTRY_DSN` boşsa hiçbir şey yapmaz, kod Sentry'nin varlığından habersiz
çalışmaya devam eder. DSN doluysa `sentry_sdk.init()` çağrılır — bu da
kendi içinde bir try/except ile sarılı, çünkü gözlemlenebilirlik altyapısının
kurulumu asla uygulamanın ayağa kalkmasını engellememeli (proje kuralı:
"Exception'ları yut, logla, fallback dön — servis çökmemeli").

Hem `app` hem `worker` process'inde ayrı ayrı çağrılır (`main.py` ve
`kafka_consumer.py`), her ikisi de Sentry'de `server_name`/`environment`
etiketiyle ayırt edilebilir.
"""

import logging

from src.infrastructure.config.settings import settings

log = logging.getLogger(__name__)


def init_sentry(component: str) -> None:
    """SENTRY_DSN yapılandırılmışsa Sentry SDK'sını başlatır.

    Args:
        component: "app" veya "worker" — Sentry event'lerinde hangi
            process'ten geldiğini ayırt etmek için `server_name` etiketi.
    """
    if not settings.sentry_dsn:
        return
    try:
        import sentry_sdk

        sentry_sdk.init(
            dsn=settings.sentry_dsn,
            environment=settings.environment,
            server_name=component,
            traces_sample_rate=settings.sentry_traces_sample_rate,
        )
        log.info("Sentry hata takibi aktif (component=%s, environment=%s).", component, settings.environment)
    except Exception:
        # Sentry kurulumu ASLA uygulamanın açılışını engellememeli.
        log.exception("Sentry başlatılamadı, hata takibi olmadan devam ediliyor.")
