"""frontend/lib/topics.ts ÜRETİLEN bir dosyadır; kayıt defteriyle kayarsa CI kırmızı olmalı."""
import importlib.util
from pathlib import Path

import pytest as _pytest_drift

pytestmark = _pytest_drift.mark.drift

ROOT = Path(__file__).resolve().parents[2]


def _render() -> str:
    spec = importlib.util.spec_from_file_location("gen_frontend_topics", ROOT / "scripts" / "gen_frontend_topics.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.render()


def test_generated_frontend_topics_match_registry():
    actual = (ROOT / "frontend" / "lib" / "topics.ts").read_text(encoding="utf-8").replace("\r\n", "\n")
    assert actual == _render(), "frontend/lib/topics.ts eski — çalıştır: python scripts/gen_frontend_topics.py"
