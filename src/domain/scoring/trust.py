"""Görünür "güven skoru" — quality/credibility/corroboration'ı tek bir 0-100
sayıya birleştiren saf hesap, dış bağımlılık yok (bkz. quality.py/credibility.py
ile aynı felsefe). SAKLANMAZ — her okumada hesaplanır, çünkü corroboration_count
zamanla artabilir (yeni bir kaynak aynı olayı doğrularsa) ve saklanan bir değer
bu durumda bayatlar.

31 Ağu 2026 (kullanıcı isteği): `NewsCard`'daki rozetin hover metni her
haberde AYNI statik yüzdeleri ("kaynak güvenilirliği %45" gibi) yazıyordu —
o haberin GERÇEKTEN kaç puan aldığını göstermiyordu. `trust_score_breakdown`
bunun için eklendi; `compute_trust_score` artık onun parçalarının TOPLAMI
(round(sum) DEĞİL, sum(round(parça))) — kullanıcı hover'daki 3 sayıyı elle
toplasa, kartın üstündeki toplamla HER ZAMAN eşleşsin diye bilinçli tercih.
"""
from typing import Optional

_QUALITY_WEIGHT = 0.35
_CREDIBILITY_WEIGHT = 0.45
_CORROBORATION_WEIGHT = 0.20
_CORROBORATION_FULL_AT = 3  # bu sayıda doğrulayan kaynaktan sonra tam puan


def trust_score_breakdown(
    quality_score: Optional[float],
    credibility_score: Optional[float],
    corroboration_count: int,
) -> dict:
    """Her bileşenin 100 puanlık toplama kaç puan kattığını döner —
    "quality" en fazla 35, "credibility" en fazla 45, "corroboration" en
    fazla 20 (ağırlıkların kendisi, `_QUALITY_WEIGHT` vb.). Frontend'de
    `NewsCard`'ın güven rozeti hover metni bunu haber-başına gerçek sayı
    göstermek için kullanır — bkz. `trustScoreText` (NewsCard.tsx)."""
    # `or 0.5` DEĞİL — 0.0 meşru bir değer, is not None kontrolü şart.
    q = quality_score if quality_score is not None else 0.5
    c = credibility_score if credibility_score is not None else 0.5
    corr = min((corroboration_count or 0) / _CORROBORATION_FULL_AT, 1.0)
    return {
        "quality": round(100 * _QUALITY_WEIGHT * q),
        "credibility": round(100 * _CREDIBILITY_WEIGHT * c),
        "corroboration": round(100 * _CORROBORATION_WEIGHT * corr),
    }


def compute_trust_score(
    quality_score: Optional[float],
    credibility_score: Optional[float],
    corroboration_count: int,
) -> int:
    return sum(trust_score_breakdown(quality_score, credibility_score, corroboration_count).values())
