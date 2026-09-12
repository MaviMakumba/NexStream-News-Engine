"""security_events tablosu erişimi (13 Eylül 2026).

Yazma tek noktadan (`record`), okuma admin paneli için filtreli (`query`),
silme retention job için (`delete_older_than`). Uzun alanlar burada kırpılır
ki çağıran tarafların hiçbiri kolon sınırını düşünmek zorunda kalmasın.
"""

from datetime import datetime
from typing import List, Optional

from sqlalchemy.orm import Session

from src.adapters.repositories.orm_models import SecurityEventORM
from src.domain.models.security_event import SecurityEvent, USER_AGENT_MAX_LEN, DETAIL_MAX_LEN


def _clip(value: Optional[str], limit: int) -> Optional[str]:
    if value is None:
        return None
    return value[:limit]


class SecurityEventRepository:
    def __init__(self, db: Session):
        self.db = db

    @staticmethod
    def _to_domain(orm: SecurityEventORM) -> SecurityEvent:
        return SecurityEvent(
            id=orm.id, category=orm.category, event_type=orm.event_type,
            email=orm.email, user_id=orm.user_id, ip=orm.ip, user_agent=orm.user_agent,
            request_id=orm.request_id, path=orm.path, detail=orm.detail, created_at=orm.created_at,
        )

    def record(self, event: SecurityEvent) -> SecurityEvent:
        orm = SecurityEventORM(
            category=event.category,
            event_type=event.event_type,
            email=event.email.strip().lower() if event.email else None,
            user_id=event.user_id,
            ip=_clip(event.ip, 64),
            user_agent=_clip(event.user_agent, USER_AGENT_MAX_LEN),
            request_id=_clip(event.request_id, 64),
            path=_clip(event.path, 255),
            detail=_clip(event.detail, DETAIL_MAX_LEN),
        )
        self.db.add(orm)
        self.db.commit()
        self.db.refresh(orm)
        return self._to_domain(orm)

    def query(
        self,
        email: Optional[str] = None,
        ip: Optional[str] = None,
        event_type: Optional[str] = None,
        since: Optional[datetime] = None,
        limit: int = 200,
    ) -> List[SecurityEvent]:
        q = self.db.query(SecurityEventORM)
        if email:
            q = q.filter(SecurityEventORM.email == email.strip().lower())
        if ip:
            q = q.filter(SecurityEventORM.ip == ip.strip())
        if event_type:
            q = q.filter(SecurityEventORM.event_type == event_type)
        if since is not None:
            q = q.filter(SecurityEventORM.created_at >= since)
        rows = q.order_by(SecurityEventORM.created_at.desc(), SecurityEventORM.id.desc()).limit(limit).all()
        return [self._to_domain(r) for r in rows]

    def delete_older_than(self, cutoff: datetime) -> int:
        removed = self.db.query(SecurityEventORM).filter(SecurityEventORM.created_at < cutoff).delete()
        self.db.commit()
        return removed

    def _set_created_at(self, event_id: int, when: datetime) -> None:
        """Test yardımcısı — retention/since senaryoları için zaman damgasını geri alır."""
        self.db.query(SecurityEventORM).filter(SecurityEventORM.id == event_id).update({"created_at": when})
        self.db.commit()
