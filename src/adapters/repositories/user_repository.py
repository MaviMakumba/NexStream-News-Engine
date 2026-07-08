"""Kullanıcı repository'sinin PostgreSQL (SQLAlchemy) implementasyonu.

`UserRepositoryPort` sözleşmesini gerçekler: kullanıcı CRUD, oturum yönetimi
ve API kullanım takibi (kota sayacı + istatistik). ORM ↔ domain dönüşümleri
`_to_user` / `_to_session` yardımcılarında toplanır; router'lar asla ORM
nesnesi görmez.
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import List, Optional

from sqlalchemy import Date, func
from sqlalchemy.orm import Session

from src.domain.models.user import User, UserSession, UserTier, UserRole, PasswordResetToken
from src.domain.ports.user_port import UserRepositoryPort
from src.adapters.repositories.orm_models import UserORM, UserSessionORM, UsageLogORM, PasswordResetTokenORM

logger = logging.getLogger(__name__)


class UserRepository(UserRepositoryPort):
    def __init__(self, db: Session):
        self.db = db

    # ── ORM ↔ Domain dönüşümleri ───────────────────────────────────────────

    def _to_user(self, orm: UserORM) -> User:
        return User(
            id=orm.id,
            email=orm.email,
            password_hash=orm.password_hash,
            name=orm.name or "",
            tier=UserTier(orm.tier),
            is_active=orm.is_active,
            role=UserRole(getattr(orm, "role", None) or "user"),
            api_key=getattr(orm, "api_key", None),
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

    def _to_reset_token(self, orm: PasswordResetTokenORM) -> PasswordResetToken:
        return PasswordResetToken(
            id=orm.id,
            user_id=orm.user_id,
            token=orm.token,
            expires_at=orm.expires_at,
            used=orm.used,
            created_at=orm.created_at,
        )

    # ── Kullanıcı CRUD ─────────────────────────────────────────────────────

    def create_user(self, user: User) -> User:
        orm = UserORM(
            email=user.email,
            password_hash=user.password_hash,
            name=user.name,
            tier=user.tier.value if isinstance(user.tier, UserTier) else user.tier,
            is_active=user.is_active,
            role=user.role.value if isinstance(user.role, UserRole) else user.role,
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

    def get_by_api_key(self, api_key: str) -> Optional[User]:
        orm = self.db.query(UserORM).filter(UserORM.api_key == api_key).first()
        return self._to_user(orm) if orm else None

    def list_users(self, limit: int = 50, offset: int = 0, tier: Optional[str] = None) -> List[User]:
        query = self.db.query(UserORM).order_by(UserORM.created_at.desc())
        if tier:
            query = query.filter(UserORM.tier == tier)
        rows = query.offset(offset).limit(limit).all()
        return [self._to_user(r) for r in rows]

    def count_users(self, tier: Optional[str] = None) -> int:
        query = self.db.query(func.count(UserORM.id))
        if tier:
            query = query.filter(UserORM.tier == tier)
        return query.scalar() or 0

    def update_tier(self, user_id: int, tier: str, stripe_customer_id: Optional[str] = None) -> bool:
        orm = self.db.query(UserORM).filter(UserORM.id == user_id).first()
        if not orm:
            return False
        orm.tier = tier
        if stripe_customer_id:
            orm.stripe_customer_id = stripe_customer_id
        self.db.commit()
        return True

    def update_role(self, user_id: int, role: str) -> bool:
        orm = self.db.query(UserORM).filter(UserORM.id == user_id).first()
        if not orm:
            return False
        orm.role = role
        self.db.commit()
        return True

    def set_api_key(self, user_id: int, api_key: Optional[str]) -> bool:
        orm = self.db.query(UserORM).filter(UserORM.id == user_id).first()
        if not orm:
            return False
        orm.api_key = api_key
        self.db.commit()
        return True

    def update_password(self, user_id: int, password_hash: str) -> bool:
        orm = self.db.query(UserORM).filter(UserORM.id == user_id).first()
        if not orm:
            return False
        orm.password_hash = password_hash
        self.db.commit()
        return True

    # ── Oturum yönetimi ────────────────────────────────────────────────────

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

    def delete_sessions_for_user(self, user_id: int) -> None:
        self.db.query(UserSessionORM).filter(UserSessionORM.user_id == user_id).delete()
        self.db.commit()

    # ── Şifre sıfırlama ────────────────────────────────────────────────────

    def create_reset_token(self, reset_token: PasswordResetToken) -> PasswordResetToken:
        orm = PasswordResetTokenORM(
            user_id=reset_token.user_id,
            token=reset_token.token,
            expires_at=reset_token.expires_at,
        )
        self.db.add(orm)
        self.db.commit()
        self.db.refresh(orm)
        return self._to_reset_token(orm)

    def get_reset_token(self, token: str) -> Optional[PasswordResetToken]:
        orm = (
            self.db.query(PasswordResetTokenORM)
            .filter(PasswordResetTokenORM.token == token)
            .first()
        )
        return self._to_reset_token(orm) if orm else None

    def mark_reset_token_used(self, token: str) -> None:
        orm = self.db.query(PasswordResetTokenORM).filter(PasswordResetTokenORM.token == token).first()
        if orm:
            orm.used = True
            self.db.commit()

    # ── Kullanım takibi ────────────────────────────────────────────────────

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
        """Endpoint bazında istek sayısı ve ortalama yanıt süresi döner.

        user_id verilirse tek kullanıcıya filtrelenir (self-service panel);
        verilmezse tüm kullanıcıları kapsar (admin paneli).
        """
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
        """Bugünkü (UTC) istek sayısı — tier kota kontrolünde kullanılır."""
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
