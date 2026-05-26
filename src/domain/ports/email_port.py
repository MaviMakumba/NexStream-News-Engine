from abc import ABC, abstractmethod
from typing import List
from src.domain.models.article import Article


class EmailPort(ABC):
    @abstractmethod
    def send_digest(self, to: str, articles: List[Article], language: str) -> bool: ...

    @abstractmethod
    def send_alert(self, to: str, article: Article, matched_keyword: str) -> bool: ...

    @abstractmethod
    def send_welcome(self, to: str, language: str) -> bool: ...
