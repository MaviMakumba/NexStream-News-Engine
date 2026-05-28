"""Deterministik içerik kalite skorlama — LLM gerektirmez.

Skor [0, 1] aralığında: uzunluk, entity yoğunluğu, özet ve başlık göstergeleri.
Düşük skorlu haberler API/dashboard'da min_quality filtresiyle gizlenebilir.
"""
from src.domain.models.article import Article

# Ağırlıklar toplamı 1.0 olacak şekilde seçildi.
_LENGTH_WEIGHT = 0.40
_ENTITY_WEIGHT = 0.35
_SUMMARY_WEIGHT = 0.15
_TITLE_WEIGHT = 0.10

_LENGTH_FULL_AT = 600   # bu uzunluktan sonra tam puan
_ENTITY_FULL_AT = 5     # bu sayıda entity'den sonra tam puan


def _entity_count(entities) -> int:
    if not isinstance(entities, dict):
        return 0
    return sum(len(v) for v in entities.values() if isinstance(v, list))


def compute_quality_score(article: Article) -> float:
    content = article.content or ""
    summary = article.summary or ""
    title = article.title or ""

    length_score = min(len(content) / _LENGTH_FULL_AT, 1.0) * _LENGTH_WEIGHT
    entity_score = min(_entity_count(article.entities) / _ENTITY_FULL_AT, 1.0) * _ENTITY_WEIGHT
    summary_score = _SUMMARY_WEIGHT if len(summary) >= 20 else 0.0
    title_score = _TITLE_WEIGHT if 15 <= len(title) <= 200 else 0.0

    return round(length_score + entity_score + summary_score + title_score, 4)
