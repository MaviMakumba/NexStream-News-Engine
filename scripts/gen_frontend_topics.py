"""frontend/lib/topics.ts dosyasını src/domain/topics.py kayıt defterinden üretir.

Çalıştır: python scripts/gen_frontend_topics.py
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.domain.topics import TOPICS  # noqa: E402

OUT = ROOT / "frontend" / "lib" / "topics.ts"


def render() -> str:
    rows = ",\n".join(
        f"  {{ id: {json.dumps(t.id)}, labels: {json.dumps(dict(t.labels), ensure_ascii=False)} }}" for t in TOPICS
    )
    return (
        "// ÜRETİLDİ — ELLE DÜZENLEME. Kaynak: src/domain/topics.py\n"
        "// Yeniden üret: python scripts/gen_frontend_topics.py (tests/infrastructure/test_frontend_topics_sync.py kaymayı yakalar)\n"
        f"export const TOPICS = [\n{rows},\n] as const;\n\n"
        'export type TopicId = (typeof TOPICS)[number]["id"];\n'
    )


if __name__ == "__main__":
    OUT.write_text(render(), encoding="utf-8", newline="\n")
    print(f"yazıldı: {OUT}")
