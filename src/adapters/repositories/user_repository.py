import logging
from datetime import datetime, timezone, timedelta
from typing import List, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from src.domain.models.user import User, UserSession, UserTier
from src.domain.ports.user_port import UserRepositoryPort
from src.adapters.repositories.orm_models import UserORM, UserSessionORM, UsageLogORM

logger = logging.getLogger(__name__)


class UserRepository(UserRepositoryPort):
    def __init__(self, db: Session):
        self.db = db

    def _to_user(self, orm: UserORM) -> User:
        return User(
            id=orm.id,
            email=orm.email,
            password_hash=orm.password_hash,
            name=orm.name or "",
            tier=UserTier(orm.tier),
            is_active=orm.is_active,
            stripe_customer_id=orm.stripe_customer_id,
            created_at=orm.created_at,
        )

    def _to_session(self, orm: UserSessionORM) -> UserSession:
        return UserSession(
            id=orm.id,
            user_id=orm.user_id,
            token=orm.token,
            expires_at=orm.expires_at,
            created_at=orm.created_at,
        )

    def create_user(self, user: User) -> User:
        orm = UserORM(
            email=user.email,
            password_hash=user.password_hash,
            name=user.name,
            tier=user.tier.value if isinstance(user.tier, UserTier) else user.tier,
            is_active=user.is_active,
            stripe_customer_id=user.stripe_customer_id,
        )
        self.db.add(orm)
        self.db.commit()
        self.db.refresh(orm)
        return self._to_user(orm)

    def get_by_email(self, email: str) -> Optional[User]:
        orm = self.db.query(UserORM).filter(UserORM.email == email).first()
        return self._to_user(orm) if orm else None

    def get_by_id(self, user_id: int) -> Optional[User]:
        orm = self.db.query(UserORM).filter(UserORM.id == user_id).first()
        return self._to_user(orm) if orm else None

    def update_tier(self, user_id: int, tier: str, stripe_customer_id: Optional[str] = None) -> bool:
        orm = self.db.query(UserORM).filter(UserORM.id == user_id).first()
        if not orm:
            return False
        orm.tier = tier
        if stripe_customer_id:
            orm.stripe_customer_id = stripe_customer_id
        self.db.commit()
        return True

    def create_session(self, session: UserSession) -> UserSession:
        orm = UserSessionORM(
            user_id=session.user_id,
            token=session.token,
            expires_at=session.expires_at,
        )
        self.db.add(orm)
        self.db.commit()
        self.db.refresh(orm)
        return self._to_session(orm)

    def get_session(self, token: str) -> Optional[UserSession]:
        orm = (
            self.db.query(UserSessionORM)
            .filter(UserSessionORM.token == token)
            .first()
        )
        return self._to_session(orm) if orm else None

    def delete_session(self, token: str) -> bool:
        orm = self.db.query(UserSessionORM).filter(UserSessionORM.token == token).first()
        if not orm:
            return False
        self.db.delete(orm)
        self.db.commit()
        return True

    def log_usage(self, user_id: Optional[int], endpoint: str, method: str, status_code: int, response_ms: float) -> None:
        entry = UsageLogORM(
            user_id=user_id,
            endpoint=endpoint,
            method=method,
            status_code=status_code,
            response_ms=response_ms,
        )
        self.db.add(entry)
        self.db.commit()

    def get_usage_stats(self, user_id: Optional[int] = None, days: int = 30) -> List[dict]:
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        query = self.db.query(
            UsageLogORM.user_id,
            UsageLogORM.endpoint,
            func.count(UsageLogORM.id).label("count"),
            func.avg(UsageLogORM.response_ms).label("avg_ms"),
        ).filter(UsageLogORM.created_at >= cutoff)
        if user_id is not None:
            query = query.filter(UsageLogORM.user_id == user_id)
        rows = query.group_by(UsageLogORM.user_id, UsageLogORM.endpoint).all()
        return [
            {"user_id": r.user_id, "endpoint": r.endpoint, "count": r.count, "avg_ms": round(r.avg_ms or 0, 1)}
            for r in rows
        ]

    def get_daily_usage_count(self, user_id: int) -> int:
        from sqlalchemy import cast, Date
        today = datetime.now(timezone.utc).date()
        return (
            self.db.query(func.count(UsageLogORM.id))
            .filter(
                UsageLogORM.user_id == user_id,
                func.cast(UsageLogORM.created_at, Date) == today,
            )
            .scalar()
            or 0
        )
