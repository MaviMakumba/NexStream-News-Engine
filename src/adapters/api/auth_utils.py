from datetime import datetime, timezone
from typing import Optional

from fastapi import Depends, Header, HTTPException
from sqlalchemy.orm import Session

from src.infrastructure.config.database import get_db
from src.adapters.repositories.user_repository import UserRepository
from src.domain.models.user import User, UserTier, TIER_DAILY_LIMITS


def get_optional_user(
    x_session_token: Optional[str] = Header(None),
    db: Session = Depends(get_db),
) -> Optional[User]:
    if not x_session_token:
        return None
    repo = UserRepository(db)
    session = repo.get_session(x_session_token)
    if not session:
        return None
    expires = session.expires_at
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=timezone.utc)
    if expires < datetime.now(timezone.utc):
        repo.delete_session(x_session_token)
        return None
    return repo.get_by_id(session.user_id)


def get_current_user(user: Optional[User] = Depends(get_optional_user)) -> User:
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")
    return user


def check_tier_limit(
    user: Optional[User] = Depends(get_optional_user),
    db: Session = Depends(get_db),
) -> Optional[User]:
    if user is None:
        return None
    limit = TIER_DAILY_LIMITS.get(user.tier)
    if limit is None:
        return user
    repo = UserRepository(db)
    count = repo.get_daily_usage_count(user.id)
    if count >= limit:
        raise HTTPException(
            status_code=429,
            detail=f"Daily API limit reached ({limit} req/day). Upgrade your plan for higher limits.",
            headers={"X-Tier": user.tier, "X-Daily-Limit": str(limit)},
        )
    return user
