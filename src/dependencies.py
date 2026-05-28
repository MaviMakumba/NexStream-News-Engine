from fastapi import Depends
from sqlalchemy.orm import Session
from src.infrastructure.config.database import get_db
from src.adapters.repositories.news_repository import NewsRepository
from src.adapters.analysis.factory import build_analyzer
from src.adapters.search.chroma_search_repository import ChromaSearchRepository
from src.application.services.news_service import NewsService
from src.domain.ports.messaging_port import MessagePublisherPort

_message_publisher: MessagePublisherPort = None
_search_repository: ChromaSearchRepository = None
_notifier = None


def set_message_publisher(publisher: MessagePublisherPort):
    global _message_publisher
    _message_publisher = publisher


def get_message_publisher() -> MessagePublisherPort:
    if not _message_publisher:
        raise RuntimeError("Message Publisher başlatılmadı!")
    return _message_publisher


def get_search_repository() -> ChromaSearchRepository:
    global _search_repository
    if _search_repository is None:
        _search_repository = ChromaSearchRepository()
    return _search_repository


def set_notifier(notifier) -> None:
    global _notifier
    _notifier = notifier


def get_notifier():
    return _notifier


def get_news_service(db: Session = Depends(get_db)) -> NewsService:
    repo = NewsRepository(db)
    analyzer = build_analyzer()
    search_repo = get_search_repository()
    return NewsService(repository=repo, analyzer=analyzer, search_repository=search_repo)