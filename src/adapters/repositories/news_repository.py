import logging
import re
from sqlalchemy import or_
from sqlalchemy.orm import Session
from typing import List, Optional
from src.domain.ports.news_repository_port import NewsRepositoryPort
from src.domain.models.article import Article
from src.adapters.repositories.orm_models import NewsORM

logger = logging.getLogger(__name__)


class NewsRepository(NewsRepositoryPort):
    """
    NewsRepositoryPort sözleşmesini imzalayan PostgreSQL işçisi.
    Saf Article nesnelerini alır, NewsORM nesnesine çevirir (Mapper) ve kaydeder.
    """
    def __init__(self, db: Session):
        self.db = db

    # --- ÇEVİRMENLER (MAPPERS) ---
    def _to_orm(self, article: Article) -> NewsORM:
        return NewsORM(
            title=article.title,
            source=article.source,
            url=article.url,
            content=article.content,
            summary=article.summary,
            sentiment_score=article.sentiment_score,
            sentiment_label=article.sentiment_label,
        )

    def _to_domain(self, orm: NewsORM) -> Article:
        return Article(
            id=orm.id,
            title=orm.title,
            source=orm.source,
            url=orm.url,
            content=orm.content or "",
            summary=orm.summary,
            sentiment_score=orm.sentiment_score,
            sentiment_label=orm.sentiment_label,
            created_at=orm.created_at,
        )

    # --- SÖZLEŞME (PORT) METOTLARI ---
    def article_exists(self, url: str) -> bool:
        return self.db.query(NewsORM).filter(NewsORM.url == url).first() is not None

    def save_article(self, article: Article) -> bool:
        if self.article_exists(article.url):
            return False
            
        try:
            orm_obj = self._to_orm(article)
            self.db.add(orm_obj)
            self.db.commit()
            return True
        except Exception as e:
            self.db.rollback()
            logger.error("DB kayıt hatası: %s", e)
            return False

    def get_latest_news(self, limit: int, sentiment_filter: Optional[str] = None) -> List[Article]:
        query = self.db.query(NewsORM)
        if sentiment_filter:
            query = query.filter(NewsORM.sentiment_label.ilike(f"%{sentiment_filter}%"))

        rows = query.order_by(NewsORM.created_at.desc()).limit(limit).all()
        return [self._to_domain(row) for row in rows]

    def get_all_articles(self) -> List[Article]:
        rows = self.db.query(NewsORM).all()
        return [self._to_domain(row) for row in rows]

    def keyword_search(self, query: str, limit: int = 10, source: Optional[str] = None, sentiment: Optional[str] = None) -> List[Article]:
        words = [w for w in re.findall(r"\w+", query.lower()) if len(w) >= 2]
        if not words:
            return []

        # Her kelime için title/content/summary'de ilike — kelimelerden EN AZ BİRİ eşleşmeli (OR).
        # Birden çok eşleşen makaleyi sıralamak service katmanının işi (_keyword_relevance).
        word_conditions = [
            or_(
                NewsORM.title.ilike(f"%{w}%"),
                NewsORM.content.ilike(f"%{w}%"),
                NewsORM.summary.ilike(f"%{w}%"),
            )
            for w in words
        ]
        q = self.db.query(NewsORM).filter(or_(*word_conditions))

        if source:
            q = q.filter(NewsORM.source == source)
        if sentiment:
            q = q.filter(NewsORM.sentiment_label.ilike(f"%{sentiment}%"))

        rows = q.order_by(NewsORM.created_at.desc()).limit(limit).all()
        return [self._to_domain(row) for row in rows]