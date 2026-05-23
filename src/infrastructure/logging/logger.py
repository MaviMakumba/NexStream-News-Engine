import json
import logging
import sys
from datetime import datetime, timezone
from src.infrastructure.config.settings import settings


class _JSONFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        entry = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        if record.exc_info:
            entry["exc"] = self.formatException(record.exc_info)
        return json.dumps(entry, ensure_ascii=False)


class _TextFormatter(logging.Formatter):
    FMT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    DATEFMT = "%Y-%m-%d %H:%M:%S"

    def __init__(self):
        super().__init__(fmt=self.FMT, datefmt=self.DATEFMT)


def setup_logging() -> None:
    level = getattr(logging, settings.log_level.upper(), logging.INFO)
    formatter: logging.Formatter = (
        _JSONFormatter() if settings.log_format == "json" else _TextFormatter()
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root = logging.getLogger()
    root.setLevel(level)
    if root.handlers:
        root.handlers.clear()
    root.addHandler(handler)
