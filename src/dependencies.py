from fastapi import Depends
from sqlalchemy.orm import Session
from src.infrastructure.config.database import get_db
from src.adapters.repositories.news_repository import NewsRepository
from src.adapters.analysis.textblob_analyzer import TextBlobAnalyzer
from src.application.services.news_service import NewsService

def get_news_service(db: Session = Depends(get_db)) -> NewsService:
    repo = NewsRepository(db)
    analyzer = TextBlobAnalyzer()
    return NewsService(repository=repo, analyzer=analyzer)