"""Logger modülü web framework'e BAĞIMLI OLMAMALI (13 Eylül 2026 prod kesintisi).

`logger.py` request_id için `adapters/api/request_context`'i import edince o da
`fastapi`'yi çekti; scheduler `Dockerfile.light` (requirements-light, fastapi
YOK) ile çalıştığı için `setup_logging` import'unda `ModuleNotFoundError` ile
crash-loop'a girdi (restarts=10, 10 dk boyunca scrape tetiklenmedi). Kural:
`src/infrastructure/*` HİÇBİR ZAMAN `src/adapters/*` import etmez (bağımlılık
yönü Adapter → Application → Domain, infrastructure en altta); request_id
ContextVar'ı bu yüzden infrastructure'da yaşar, adapter onu sarar.
"""

import subprocess
import sys


def _imports_pull(module: str, forbidden: str) -> bool:
    code = (
        f"import sys; import {module}; "
        f"print(any(m == '{forbidden}' or m.startswith('{forbidden}.') for m in sys.modules))"
    )
    out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, check=True)
    return out.stdout.strip() == "True"


def test_logger_does_not_import_fastapi():
    assert _imports_pull("src.infrastructure.logging.logger", "fastapi") is False


def test_logger_does_not_import_adapters():
    assert _imports_pull("src.infrastructure.logging.logger", "src.adapters") is False


def test_scheduler_entrypoint_does_not_import_fastapi():
    """Light image'ın gerçek giriş noktası — scheduler_service import edilebilmeli."""
    assert _imports_pull("src.adapters.scheduling.scheduler_service", "fastapi") is False
