"""Kaydedilen haber (bookmark) repository port'u — v2.2.

Somut implementasyon: adapters/repositories/saved_article_repository.py (PostgreSQL).
"""

from abc import ABC, abstractmethod
from typing import List


class SavedArticlePort(ABC):
    @abstractmethod
    def save(self, user_id: int, article_id: int) -> bool:
        """Kaydeder; zaten kayıtlıysa idempotent (True döner, ikinci satır açılmaz)."""

    @abstractmethod
    def unsave(self, user_id: int, article_id: int) -> bool:
        """Kaldırır; kayıtlı değilse False döner."""

    @abstractmethod
    def is_saved(self, user_id: int, article_id: int) -> bool: ...

    @abstractmethod
    def list_saved_article_ids(self, user_id: int) -> List[int]:
        """En son kaydedilen önce olacak şekilde article_id listesi."""

    @abstractmethod
    def delete_for_user(self, user_id: int) -> None:
        """Hesap silinirken kullanıcının tüm kayıtlarını temizler."""
