"""Alım (ingest) politikası — analiz bütçesi kime harcanır (29 Eylül 2026, S2).

Groq günlük token kotası doyduğunda (prod'da akşamları iki model de tükeniyor)
bütçenin ESKİ habere gitmesi kullanıcı için değersiz: dünkü maçın yayın saati
haberi analiz edilirken bugünün haberi sırada bekliyor. Bu politika saf bir
fonksiyondur: yaş süzgeci, tazelik sıralaması ve bütçe sınırı tek yerde.
"""

from datetime import datetime, timedelta, timezone
from typing import List, Optional

from src.domain.models.article import Article


def _aware(moment: datetime) -> datetime:
    """Tz'siz tarihler UTC varsayılır (bazı feed'ler bölge bilgisi vermez)."""
    return moment if moment.tzinfo else moment.replace(tzinfo=timezone.utc)


def _newest_first_key(article: Article):
    """Tarihliler önce (yeni → eski), tarihsizler sonda. `sorted` kararlı → eşitlerde feed sırası."""
    if article.published_at is None:
        return (1, 0.0)
    return (0, -_aware(article.published_at).timestamp())


def sort_newest_first(articles: List[Article]) -> List[Article]:
    return sorted(articles, key=_newest_first_key)


def select_for_analysis(
    articles: List[Article],
    *,
    now: datetime,
    max_age_hours: int,
    daily_budget_left: Optional[int],
    per_run_limit: Optional[int],
) -> List[Article]:
    """Bu turda analiz edilecek haberler: yeterince taze olanlar, en yeniden başlayarak,
    günlük kalan bütçe ve tur sınırının KÜÇÜĞÜ kadar. `None` = sınırsız. Yayın tarihi
    olmayan haber elenmez (yaşı bilinmiyor) ama tarihlilerin arkasına düşer."""
    oldest_allowed = now - timedelta(hours=max_age_hours)
    fresh = [a for a in articles if a.published_at is None or _aware(a.published_at) >= oldest_allowed]
    ordered = sort_newest_first(fresh)

    limits = [limit for limit in (daily_budget_left, per_run_limit) if limit is not None]
    if not limits:
        return ordered
    return ordered[:max(min(limits), 0)]
