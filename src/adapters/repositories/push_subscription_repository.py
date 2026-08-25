"""Web push abonelik repository'sinin PostgreSQL implementasyonu — v2.5.

`PushSubscriptionRepositoryPort` sözleşmesini gerçekler. `endpoint` üzerinde
UNIQUE index var (bkz. orm_models.py) — `save` bu yüzden upsert: aynı endpoint
tekrar gelirse (tarayıcı subscription'ı yeniledi) üzerine yazar.
"""

import logging
from typing import List

from sqlalchemy.orm import Session

from src.domain.models.push_subscription import PushSubscription
from src.domain.ports.push_subscription_port import PushSubscriptionRepositoryPort
from src.adapters.repositories.orm_models import PushSubscriptionORM

logger = logging.getLogger(__name__)


class PushSubscriptionRepository(PushSubscriptionRepositoryPort):
    def __init__(self, db: Session):
        self.db = db

    def _to_domain(self, orm: PushSubscriptionORM) -> PushSubscription:
        return PushSubscription(
            id=orm.id, email=orm.email, endpoint=orm.endpoint,
            p256dh=orm.p256dh, auth=orm.auth, created_at=orm.created_at,
        )

    def save(self, subscription: PushSubscription) -> PushSubscription:
        existing = self.db.query(PushSubscriptionORM).filter(
            PushSubscriptionORM.endpoint == subscription.endpoint
        ).first()
        if existing:
            existing.email = subscription.email
            existing.p256dh = subscription.p256dh
            existing.auth = subscription.auth
            self.db.commit()
            self.db.refresh(existing)
            return self._to_domain(existing)
        orm = PushSubscriptionORM(
            email=subscription.email, endpoint=subscription.endpoint,
            p256dh=subscription.p256dh, auth=subscription.auth,
        )
        self.db.add(orm)
        self.db.commit()
        self.db.refresh(orm)
        return self._to_domain(orm)

    def get_by_email(self, email: str) -> List[PushSubscription]:
        rows = self.db.query(PushSubscriptionORM).filter(PushSubscriptionORM.email == email).all()
        return [self._to_domain(r) for r in rows]

    def delete_by_endpoint(self, endpoint: str) -> bool:
        orm = self.db.query(PushSubscriptionORM).filter(PushSubscriptionORM.endpoint == endpoint).first()
        if not orm:
            return False
        self.db.delete(orm)
        self.db.commit()
        return True

    def delete_by_email(self, email: str) -> None:
        self.db.query(PushSubscriptionORM).filter(PushSubscriptionORM.email == email).delete()
        self.db.commit()
