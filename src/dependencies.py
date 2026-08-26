"""FastAPI dependency injection — uygulamanın kompozisyon noktası.

Uzun ömürlü singleton'lar (Kafka publisher, ChromaDB, cache, notifier) burada
saklanır; istek başına nesneler (DB session, NewsService) dependency olarak
üretilir. Router'lar somut sınıf değil, bu fonksiyonları bilir.
"""

from fastapi import Depends
from sqlalchemy.orm import Session
from src.infrastructure.config.database import get_db
from src.adapters.repositories.news_repository import NewsRepository
from src.adapters.repositories.user_repository import UserRepository
from src.adapters.analysis.factory import build_analyzer, build_query_expander, build_question_answerer
from src.adapters.search.chroma_search_repository import ChromaSearchRepository
from src.adapters.cache.factory import build_cache
from src.adapters.market.yahoo_finance_adapter import YahooFinanceMarketAdapter
from src.application.services.news_service import NewsService
from src.domain.ports.messaging_port import MessagePublisherPort
from src.domain.ports.cache_port import CachePort
from src.domain.ports.market_data_port import MarketDataPort

_message_publisher: MessagePublisherPort = None
_search_repository: ChromaSearchRepository = None
_cache: CachePort = None
_market_data_adapter: MarketDataPort = None
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


def get_cache() -> CachePort:
    global _cache
    if _cache is None:
        _cache = build_cache()
    return _cache


def get_market_data_adapter() -> MarketDataPort:
    # Tek implementasyon var (Yahoo Finance) — build_cache()/build_analyzer()
    # gibi bir factory'ye gerek yok, get_search_repository() ile aynı
    # doğrudan-singleton deseni (YAGNI).
    global _market_data_adapter
    if _market_data_adapter is None:
        _market_data_adapter = YahooFinanceMarketAdapter()
    return _market_data_adapter


def get_user_repository(db: Session = Depends(get_db)) -> UserRepository:
    return UserRepository(db)


def get_news_service(db: Session = Depends(get_db)) -> NewsService:
    repo = NewsRepository(db)
    analyzer = build_analyzer()
    search_repo = get_search_repository()
    query_expander = build_query_expander(get_cache())
    qa_port = build_question_answerer()
    return NewsService(
        repository=repo, analyzer=analyzer,
        search_repository=search_repo, query_expander=query_expander,
        qa_port=qa_port,
    )
