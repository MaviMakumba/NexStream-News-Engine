"""E-posta port'u — digest / keyword alert / hoş geldin / doğrulama mailleri sözleşmesi.

Somut implementasyonlar: ResendEmailAdapter (RESEND_API_KEY doluysa) ve
ConsoleEmailAdapter (boşsa — mailler sadece loglanır, geliştirme modu).
"""

from abc import ABC, abstractmethod
from typing import List, Optional
from src.domain.models.article import Article


class EmailPort(ABC):
    @abstractmethod
    def send_digest(self, to: str, articles: List[Article], language: str, sponsor=None) -> bool: ...

    @abstractmethod
    def send_alert(self, to: str, article: Article, matched_keyword: str, language: str) -> bool: ...

    @abstractmethod
    def send_welcome(self, to: str, language: str) -> bool: ...

    @abstractmethod
    def send_password_reset(self, to: str, reset_url: str, language: str) -> bool: ...

    @abstractmethod
    def send_verification(self, to: str, verify_url: str, language: str) -> bool: ...
