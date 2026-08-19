"""Kaydedilen haber (bookmark / sonra oku) domain modeli — v2.2.

Kullanıcının kendi listesine eklediği haberleri temsil eder. `article_id`
`news_articles.id`'ye işaret eder ama FK CASCADE yoktur (projenin genel
deseni — bkz. UserRepository.delete_user docstring'i); hesap silindiğinde
satırlar elle temizlenir.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional


@dataclass
class SavedArticle:
    user_id: int
    article_id: int
    id: Optional[int] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
