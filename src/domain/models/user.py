from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from enum import Enum


class UserTier(str, Enum):
    FREE = "free"
    PRO = "pro"
    ENTERPRISE = "enterprise"


TIER_DAILY_LIMITS: dict = {
    UserTier.FREE: 100,
    UserTier.PRO: 2000,
    UserTier.ENTERPRISE: None,  # unlimited
}


@dataclass
class User:
    email: str
    password_hash: str
    name: str = ""
    tier: UserTier = UserTier.FREE
    is_active: bool = True
    stripe_customer_id: Optional[str] = None
    id: Optional[int] = None
    created_at: Optional[datetime] = None


@dataclass
class UserSession:
    user_id: int
    token: str
    expires_at: datetime
    id: Optional[int] = None
    created_at: Optional[datetime] = None
