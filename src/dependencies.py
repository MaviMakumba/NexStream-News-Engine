from fastapi import Depends
from sqlalchemy.orm import Session
from src.infrastructure.config.database import get_db
from src.adapters.repositories.news_repository import NewsRepository
from src.adapters.analysis.textblob_analyzer import TextBlobAnalyzer
from src.application.services.news_service import NewsService
from src.domain.ports.messaging_port import MessagePublisherPort

# Global olarak Publisher'ı tutacağımız yer (main.py burayı dolduracak)
_message_publisher: MessagePublisherPort = None

def set_message_publisher(publisher: MessagePublisherPort):
    global _message_publisher
    _message_publisher = publisher

def get_message_publisher() -> MessagePublisherPort:
    """Router'ın (API) Kafka'yı değil, 'Yayıncıyı' çağırması için Dependency."""
    if not _message_publisher:
        raise RuntimeError("Message Publisher başlatılmadı!")
    return _message_publisher

def get_news_service(db: Session = Depends(get_db)) -> NewsService:
    repo = NewsRepository(db)
    analyzer = TextBlobAnalyzer()
    return NewsService(repository=repo, analyzer=analyzer)