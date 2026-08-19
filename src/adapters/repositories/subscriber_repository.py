"""Abone repository'sinin PostgreSQL implementasyonu (SubscriberRepositoryPort)."""

import logging
from typing import List, Optional
from sqlalchemy.orm import Session
from src.domain.models.subscriber import Subscriber
from src.domain.ports.subscriber_port import SubscriberRepositoryPort
from src.adapters.repositories.orm_models import SubscriberORM

logger = logging.getLogger(__name__)


class SubscriberRepository(SubscriberRepositoryPort):
    def __init__(self, db: Session):
        self.db = db

    def _to_domain(self, orm: SubscriberORM) -> Subscriber:
        return Subscriber(
            id=orm.id,
            email=orm.email,
            keywords=orm.keywords or [],
            preferred_sources=orm.preferred_sources or [],
            preferred_topics=orm.preferred_topics or [],
            language=orm.language or "TR",
            frequency=orm.frequency or "daily",
            is_active=orm.is_active,
            created_at=orm.created_at,
        )

    def save_subscriber(self, subscriber: Subscriber) -> Subscriber:
        existing = self.db.query(SubscriberORM).filter(SubscriberORM.email == subscriber.email).first()
        if existing:
            existing.is_active = True
            existing.keywords = subscriber.keywords
            existing.preferred_sources = subscriber.preferred_sources
            existing.preferred_topics = subscriber.preferred_topics
            existing.language = subscriber.language
            existing.frequency = subscriber.frequency
            self.db.commit()
            self.db.refresh(existing)
            return self._to_domain(existing)
        orm = SubscriberORM(
            email=subscriber.email,
            keywords=subscriber.keywords,
            preferred_sources=subscriber.preferred_sources,
            preferred_topics=subscriber.preferred_topics,
            language=subscriber.language,
            frequency=subscriber.frequency,
        )
        self.db.add(orm)
        self.db.commit()
        self.db.refresh(orm)
        return self._to_domain(orm)

    def get_by_email(self, email: str) -> Optional[Subscriber]:
        orm = self.db.query(SubscriberORM).filter(SubscriberORM.email == email).first()
        return self._to_domain(orm) if orm else None

    def get_active_subscribers(self) -> List[Subscriber]:
        rows = self.db.query(SubscriberORM).filter(SubscriberORM.is_active == True).all()
        return [self._to_domain(r) for r in rows]

    def get_instant_subscribers_for_keyword(self, keyword: str) -> List[Subscriber]:
        kw_lower = keyword.lower()
        rows = (
            self.db.query(SubscriberORM)
            .filter(SubscriberORM.is_active == True, SubscriberORM.frequency == "instant")
            .all()
        )
        return [
            self._to_domain(r)
            for r in rows
            if any(kw_lower in k.lower() or k.lower() in kw_lower for k in (r.keywords or []))
        ]

    def update_subscriber(self, subscriber: Subscriber) -> bool:
        orm = self.db.query(SubscriberORM).filter(SubscriberORM.id == subscriber.id).first()
        if not orm:
            return False
        orm.keywords = subscriber.keywords
        orm.preferred_sources = subscriber.preferred_sources
        orm.preferred_topics = subscriber.preferred_topics
        orm.language = subscriber.language
        orm.frequency = subscriber.frequency
        self.db.commit()
        return True

    def deactivate(self, email: str) -> bool:
        orm = self.db.query(SubscriberORM).filter(SubscriberORM.email == email).first()
        if not orm:
            return False
        orm.is_active = False
        self.db.commit()
        return True

    def delete_by_email(self, email: str) -> bool:
        """Kaydı kalıcı olarak siler (v2.1.2, hesap silme) — `deactivate`'in
        aksine PII'yi (keywords/preferred_sources dahil) DB'de bırakmaz."""
        orm = self.db.query(SubscriberORM).filter(SubscriberORM.email == email).first()
        if not orm:
            return False
        self.db.delete(orm)
        self.db.commit()
        return True
