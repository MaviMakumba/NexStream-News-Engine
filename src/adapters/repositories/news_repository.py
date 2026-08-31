"""Haber repository'sinin PostgreSQL (SQLAlchemy) implementasyonu.

NewsRepositoryPort sözleşmesini gerçekler. ORM ↔ domain dönüşümleri _to_orm /
_to_domain mapper'larında toplanır; servis katmanı asla ORM nesnesi görmez.
Yazma hataları rollback + log ile yutulur (pipeline tek kayıt için durmaz).
"""

import logging
import re
from datetime import datetime, timezone, timedelta
from sqlalchemy import or_, func
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
            published_at=article.published_at,
            entities=article.entities,
            topic=article.topic,
            is_duplicate=article.is_duplicate,
            quality_score=article.quality_score,
            credibility_score=article.credibility_score,
            corroboration_count=article.corroboration_count,
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
            published_at=orm.published_at,
            entities=orm.entities,
            topic=orm.topic,
            is_duplicate=orm.is_duplicate or False,
            quality_score=orm.quality_score,
            credibility_score=orm.credibility_score,
            corroboration_count=orm.corroboration_count or 0,
        )

    # --- SÖZLEŞME (PORT) METOTLARI ---
    def article_exists(self, url: str) -> bool:
        return self.db.query(NewsORM).filter(NewsORM.url == url).first() is not None

    def bulk_exists(self, urls: list[str]) -> set[str]:
        if not urls:
            return set()
        rows = self.db.query(NewsORM.url).filter(NewsORM.url.in_(urls)).all()
        return {row.url for row in rows}

    def save_article(self, article: Article) -> bool:
        if self.article_exists(article.url):
            return False
            
        try:
            orm_obj = self._to_orm(article)
            self.db.add(orm_obj)
            self.db.commit()
            self.db.refresh(orm_obj)
            article.id = orm_obj.id
            return True
        except Exception as e:
            self.db.rollback()
            logger.error("DB kayıt hatası: %s", e)
            return False

    def update_article_analysis(self, article: Article) -> bool:
        try:
            orm_obj = self.db.query(NewsORM).filter(NewsORM.id == article.id).first()
            if not orm_obj:
                return False
            orm_obj.summary = article.summary
            orm_obj.sentiment_score = article.sentiment_score
            orm_obj.sentiment_label = article.sentiment_label
            orm_obj.entities = article.entities
            orm_obj.topic = article.topic
            orm_obj.quality_score = article.quality_score
            self.db.commit()
            return True
        except Exception as e:
            self.db.rollback()
            logger.error("DB güncelleme hatası: %s", e)
            return False

    def get_latest_news(self, limit: int, sentiment_filter: Optional[str] = None) -> List[Article]:
        """Ana akış — YAYIN tarihine göre sıralanır, kayıt zamanına göre DEĞİL.

        31 Ağu 2026 öncesi `created_at.desc()` kullanıyordu: worker bir kaynağın
        TÜM yeni haberlerini art arda kaydettiği için created_at kaynak bazında
        kümeleniyordu (aynı kaynağın 20+ haberi arka arkaya görünüyordu, kullanıcı
        bulgusu). `published_at` NULL ise (v1.4 öncesi scrape'ler) `created_at`e
        düşer — `get_articles_for_export`'taki coalesce deseniyle aynı disiplin.
        """
        query = self.db.query(NewsORM)
        if sentiment_filter:
            query = query.filter(NewsORM.sentiment_label.ilike(f"%{sentiment_filter}%"))

        effective_date = func.coalesce(NewsORM.published_at, NewsORM.created_at)
        rows = query.order_by(effective_date.desc()).limit(limit).all()
        return [self._to_domain(row) for row in rows]

    def get_all_articles(self) -> List[Article]:
        rows = self.db.query(NewsORM).all()
        return [self._to_domain(row) for row in rows]

    def get_unanalyzed_articles(self, limit: int = 5) -> List[Article]:
        rows = (
            self.db.query(NewsORM)
            .filter(NewsORM.entities.is_(None))
            .order_by(NewsORM.created_at.desc())
            .limit(limit)
            .all()
        )
        return [self._to_domain(row) for row in rows]

    def get_recent_articles_with_entities(self, hours: int = 6) -> List[Article]:
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
        rows = (
            self.db.query(NewsORM)
            .filter(NewsORM.created_at >= cutoff, NewsORM.entities.isnot(None))
            .all()
        )
        return [self._to_domain(row) for row in rows]

    def get_article_by_id(self, article_id: int) -> Optional[Article]:
        row = self.db.query(NewsORM).filter(NewsORM.id == article_id).first()
        return self._to_domain(row) if row else None

    def get_articles_by_ids(self, article_ids: List[int]) -> List[Article]:
        """Kaydedilenler (saved articles) listesini render etmek için toplu çekim."""
        if not article_ids:
            return []
        rows = self.db.query(NewsORM).filter(NewsORM.id.in_(article_ids)).all()
        return [self._to_domain(row) for row in rows]

    def get_articles_with_entities(self, limit: int = 500, exclude_id: Optional[int] = None) -> List[Article]:
        q = self.db.query(NewsORM).filter(NewsORM.entities.isnot(None))
        if exclude_id is not None:
            q = q.filter(NewsORM.id != exclude_id)
        rows = q.order_by(NewsORM.created_at.desc()).limit(limit).all()
        return [self._to_domain(row) for row in rows]

    def get_articles_after_id(self, article_id: int, limit: int = 20) -> List[Article]:
        rows = (
            self.db.query(NewsORM)
            .filter(NewsORM.id > article_id)
            .order_by(NewsORM.id.asc())
            .limit(limit)
            .all()
        )
        return [self._to_domain(row) for row in rows]

    def get_articles_created_after(self, cutoff: datetime) -> List[Article]:
        """Entity şartı olmadan tarih filtresi — retention job'un self-healing reindex'i kullanır."""
        rows = self.db.query(NewsORM).filter(NewsORM.created_at >= cutoff).all()
        return [self._to_domain(row) for row in rows]

    def delete_articles_before(self, cutoff: datetime) -> int:
        """KALICI silme. Sadece `db_retention_days` > 0 iken çağrılır (varsayılan kapalı)."""
        deleted = self.db.query(NewsORM).filter(NewsORM.created_at < cutoff).delete(synchronize_session=False)
        self.db.commit()
        return deleted

    def get_news_paginated(self, limit: int, before_id: Optional[int] = None, source: Optional[str] = None, sentiment: Optional[str] = None, topic: Optional[str] = None, min_quality: Optional[float] = None) -> List[Article]:
        q = self.db.query(NewsORM)
        if before_id is not None:
            q = q.filter(NewsORM.id < before_id)
        if source:
            q = q.filter(NewsORM.source == source)
        if sentiment:
            q = q.filter(NewsORM.sentiment_label.ilike(f"%{sentiment}%"))
        if topic:
            q = q.filter(NewsORM.topic == topic)
        if min_quality is not None:
            q = q.filter(NewsORM.quality_score >= min_quality)
        rows = q.order_by(NewsORM.id.desc()).limit(limit).all()
        return [self._to_domain(row) for row in rows]

    def get_articles_for_export(
        self, limit: int,
        source: Optional[str] = None,
        sentiment: Optional[str] = None,
        topic: Optional[str] = None,
        min_quality: Optional[float] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
    ) -> List[Article]:
        """Ham veri export için toplu çekim — sayfalama yok, `limit`'e kadar tüm eşleşmeler.

        Tarih filtresi `published_at`e uygulanır, NULL ise `created_at`e düşer
        (ChromaDB metadata'sındaki `published_at or created_at` fallback'iyle
        aynı desen — v1.4 öncesi scrape'lerde published_at boş olabilir).
        """
        q = self.db.query(NewsORM)
        if source:
            q = q.filter(NewsORM.source == source)
        if sentiment:
            q = q.filter(NewsORM.sentiment_label.ilike(f"%{sentiment}%"))
        if topic:
            q = q.filter(NewsORM.topic == topic)
        if min_quality is not None:
            q = q.filter(NewsORM.quality_score >= min_quality)
        if date_from is not None or date_to is not None:
            effective_date = func.coalesce(NewsORM.published_at, NewsORM.created_at)
            if date_from is not None:
                q = q.filter(effective_date >= date_from)
            if date_to is not None:
                q = q.filter(effective_date <= date_to)
        rows = q.order_by(NewsORM.id.desc()).limit(limit).all()
        return [self._to_domain(row) for row in rows]

    def keyword_search(self, query: str, limit: int = 10, source: Optional[str] = None, sentiment: Optional[str] = None, terms: Optional[List[str]] = None) -> List[Article]:
        words = terms if terms is not None else [w for w in re.findall(r"\w+", query.lower()) if len(w) >= 2]
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