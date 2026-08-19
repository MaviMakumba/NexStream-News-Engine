"""Kaydedilen haber (bookmark) repository'sinin PostgreSQL implementasyonu — v2.2.

`SavedArticlePort` sözleşmesini gerçekler. `(user_id, article_id)` üzerinde
unique index var (bkz. orm_models.py) — `save` bu yüzden idempotent: mevcut
satırı kontrol edip yoksa ekler, ikinci çağrı sessizce True döner.
"""

import logging
from typing import List

from sqlalchemy.orm import Session

from src.domain.ports.saved_article_port import SavedArticlePort
from src.adapters.repositories.orm_models import SavedArticleORM

logger = logging.getLogger(__name__)


class SavedArticleRepository(SavedArticlePort):
    def __init__(self, db: Session):
        self.db = db

    def _get(self, user_id: int, article_id: int):
        return (
            self.db.query(SavedArticleORM)
            .filter(SavedArticleORM.user_id == user_id, SavedArticleORM.article_id == article_id)
            .first()
        )

    def save(self, user_id: int, article_id: int) -> bool:
        if self._get(user_id, article_id):
            return True
        self.db.add(SavedArticleORM(user_id=user_id, article_id=article_id))
        self.db.commit()
        return True

    def unsave(self, user_id: int, article_id: int) -> bool:
        orm = self._get(user_id, article_id)
        if not orm:
            return False
        self.db.delete(orm)
        self.db.commit()
        return True

    def is_saved(self, user_id: int, article_id: int) -> bool:
        return self._get(user_id, article_id) is not None

    def list_saved_article_ids(self, user_id: int) -> List[int]:
        rows = (
            self.db.query(SavedArticleORM)
            .filter(SavedArticleORM.user_id == user_id)
            .order_by(SavedArticleORM.id.desc())
            .all()
        )
        return [r.article_id for r in rows]

    def delete_for_user(self, user_id: int) -> None:
        self.db.query(SavedArticleORM).filter(SavedArticleORM.user_id == user_id).delete()
        self.db.commit()
