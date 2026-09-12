"""RFC 9116 security.txt regresyon testi (12 Eylül 2026 güvenlik turu).

"Güvenlik araştırmacısı" maillerinin gelmesini engelleyemeyiz ama iki şeyi
belirleyebiliriz: bulguların HANGİ kanaldan geleceğini ve ödül programı
OLMADIĞINI. security.txt tarayıcı/araştırmacı araçlarının ilk baktığı yer;
`Expires` alanı RFC'de zorunlu ve geçmiş bir tarih dosyayı geçersiz sayar —
bu test tarihin sessizce dolmasını yakalar.
"""

from datetime import datetime, timezone

_PATH = "frontend/public/.well-known/security.txt"


def _fields() -> dict:
    with open(_PATH, "r", encoding="utf-8") as f:
        lines = [l.strip() for l in f if l.strip() and not l.startswith("#")]
    fields: dict = {}
    for line in lines:
        key, _, value = line.partition(":")
        fields.setdefault(key.strip(), []).append(value.strip())
    return fields


def test_security_txt_has_required_contact_and_policy():
    fields = _fields()
    assert any(c.startswith("https://nexstreamnews.com/") for c in fields["Contact"])
    assert fields["Policy"] == ["https://nexstreamnews.com/security"]
    assert fields["Canonical"] == ["https://nexstreamnews.com/.well-known/security.txt"]


def test_security_txt_expires_is_in_the_future():
    fields = _fields()
    expires = datetime.fromisoformat(fields["Expires"][0].replace("Z", "+00:00"))
    assert expires > datetime.now(timezone.utc), "security.txt Expires tarihi dolmuş — yenile"
