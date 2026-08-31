"""Görünür "güven skoru" — quality/credibility/corroboration'ı tek bir 0-100
sayıya birleştiren saf hesap, dış bağımlılık yok (bkz. quality.py/credibility.py
ile aynı felsefe). SAKLANMAZ — her okumada hesaplanır, çünkü corroboration_count
zamanla artabilir (yeni bir kaynak aynı olayı doğrularsa) ve saklanan bir değer
bu durumda bayatlar.
"""
from typing import Optional

_QUALITY_WEIGHT = 0.35
_CREDIBILITY_WEIGHT = 0.45
_CORROBORATION_WEIGHT = 0.20
_CORROBORATION_FULL_AT = 3  # bu sayıda doğrulayan kaynaktan sonra tam puan


def compute_trust_score(
    quality_score: Optional[float],
    credibility_score: Optional[float],
    corroboration_count: int,
) -> int:
    # `or 0.5` DEĞİL — 0.0 meşru bir değer, is not None kontrolü şart.
    q = quality_score if quality_score is not None else 0.5
    c = credibility_score if credibility_score is not None else 0.5
    corr = min((corroboration_count or 0) / _CORROBORATION_FULL_AT, 1.0)
    return round(100 * (_QUALITY_WEIGHT * q + _CREDIBILITY_WEIGHT * c + _CORROBORATION_WEIGHT * corr))
