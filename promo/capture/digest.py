"""Tanıtım videosu için GERÇEK bülten e-posta şablonunu kurgusal haberlerle üretir.

Kullanım (repo kökünden, capture.mjs çağırır):
    venv/Scripts/python.exe promo/capture/digest.py <TR|EN> <haberler.json> <cikti.html>

Şablonu kopyalamıyoruz: `email_adapter._digest_html` doğrudan çağrılır, yani videodaki
mail her zaman sitenin gönderdiği mail ile aynı tasarımda kalır.
"""
import json
import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
os.environ.setdefault("FRONTEND_URL", "https://nexstreamnews.com")

from src.adapters.notifications.email_adapter import _digest_html  # noqa: E402
from src.domain.models.article import Article  # noqa: E402


def main() -> None:
    lang, src, out = sys.argv[1], sys.argv[2], sys.argv[3]
    items = json.loads(Path(src).read_text(encoding="utf-8"))
    articles = [
        Article(title=a["title"], source=a["source"], url=a["url"], content="", summary=a["summary"],
                sentiment_label=a["sentiment_label"], topic=a["topic"], id=a["id"])
        for a in items
    ]
    html = _digest_html("reader@example.com", articles, lang)
    Path(out).write_text(html, encoding="utf-8")


if __name__ == "__main__":
    main()
