"""Admin güvenlik sayfasındaki olay tipi listesi (frontend, elle tutuluyor) backend
`EventType` sabitleriyle birebir aynı kalmalı. Yeni bir tip backend'e eklenip arayüze
unutulursa filtre açılır listesinde o olay hiç seçilemez (29 Eyl 2026, #30 denetimi)."""

import re
from pathlib import Path

from src.domain.models.security_event import EventType

import pytest as _pytest_drift

pytestmark = _pytest_drift.mark.drift

PAGE = Path(__file__).resolve().parents[2] / "frontend" / "app" / "admin" / "security" / "page.tsx"


def _frontend_types() -> set:
    src = PAGE.read_text(encoding="utf-8")
    block = re.search(r"const EVENT_TYPES = \[(.*?)\] as const", src, re.S).group(1)
    return set(re.findall(r'"([a-z_]+)"', block))


def test_frontend_event_type_list_matches_backend():
    backend = {v for k, v in vars(EventType).items() if k.isupper() and isinstance(v, str)}
    assert _frontend_types() == backend, (
        f"frontend'de eksik: {sorted(backend - _frontend_types())}, "
        f"backend'de olmayan: {sorted(_frontend_types() - backend)}"
    )
