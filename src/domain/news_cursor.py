"""Haber listesi sayfalama imleci — (etkin yayın zamanı, id) çiftini URL-güvenli bir string'e çevirir.

Liste yayın zamanına göre sıralı olduğu için id tek başına imleç olamaz (id =
kayıt sırası; worker eski haberi sonradan kaydedince id yayın sırasıyla
uyuşmaz). Biçim: "<epoch mikrosaniye>_<id>" — ":" ve "+" içermez, encode gerektirmez.
"""

from datetime import datetime, timezone
from typing import Optional, Tuple

Cursor = Tuple[datetime, int]


def effective_date(article) -> datetime:
    return article.published_at or article.created_at


def encode_cursor(article) -> str:
    dt = effective_date(article)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    micros = int(dt.timestamp()) * 1_000_000 + dt.microsecond
    return f"{micros}_{article.id}"


def decode_cursor(raw: str) -> Cursor:
    """Geçersizse ValueError. Eski düz-id imleçleri BURADA çözülmez (bkz. is_legacy_cursor)."""
    micros_s, sep, id_s = raw.partition("_")
    if not sep:
        raise ValueError("invalid cursor")
    micros = int(micros_s)
    dt = datetime.fromtimestamp(micros // 1_000_000, tz=timezone.utc).replace(microsecond=micros % 1_000_000)
    return dt, int(id_s)


def legacy_cursor_id(raw: str) -> Optional[int]:
    """Yayın-zamanı öncesi sürümün düz sayısal imleci ("123") ise id'yi döner."""
    return int(raw) if raw.isdigit() else None
